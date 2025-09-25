import structlog
from langgraph.graph import END, StateGraph
from pydantic_ai import Agent
from sqlalchemy import text

from src.schemas.agent_schemas import GraphState, Intent, ThoughtAndSQL

# 로거 설정
logger = structlog.get_logger(__name__)

# --- Agent Nodes ---


async def intent_classifier_node(state: GraphState):
    """Classifies the user's question intent using an LLM agent."""
    logger.info("Executing node: intent_classifier")

    intent_agent = Agent("openai:gpt-4o", output_type=Intent)

    prompt = f"""
    Classify the user's intent based on their question into one of the following categories: "sql_generation", "greeting", "chit_chat", or "unknown".

    - For work-related questions involving data lookup or analysis, classify as "sql_generation".
    - If the intent is unclear, you must classify it as "unknown".

    User Question: {state["question"]}
    """

    try:
        result = await intent_agent.run(prompt)
        intent = result.output.intent
        logger.info("Intent classification complete", intent=intent)
    except Exception as e:
        logger.error(
            "Error during intent classification", error=str(e), exc_info=True
        )
        intent = "unknown"

    # Initialize thoughts list
    return {"intent": intent, "thoughts": [], "messages": []}


async def sql_generator_node(state: GraphState):
    """Generates a SQL query and a thought about it."""
    logger.info("Executing node: sql_generator")

    reflection_feedback = "\n".join(state.get("reflection", []))

    prompt = f"""
    You are a PostgreSQL database expert. Your goal is to generate a SQL query to answer the user's question.
    First, think about the user's question and the database schema to devise a plan.
    Then, generate the SQL query based on your plan.

    ### Database Schema:
    {state["db_schema"]}

    ### Feedback from previous attempts (if any):
    {reflection_feedback if reflection_feedback else "None"}

    ### User Question:
    {state["question"]}
    
    The final query must be a single, valid PostgreSQL SELECT statement ending with a semicolon.
    """

    sql_agent = Agent("openai:gpt-4o", output_type=ThoughtAndSQL)

    try:
        result = await sql_agent.run(prompt)
        thought = result.output.thought
        sql_query = result.output.query

        logger.info(
            "SQL generation successful", thought=thought, sql_query=sql_query
        )

        # Add thought to state
        thoughts = state.get("thoughts", []) + [thought]

        return {"thoughts": thoughts, "sql_query": sql_query}

    except Exception as e:
        logger.error("Error during SQL generation", error=str(e), exc_info=True)
        # Set reflection to indicate error and route to final_answer
        return {"reflection": [f"Error during SQL generation: {e}"]}


async def reflection_node(state: GraphState):
    """Validates the generated SQL query and suggests improvements."""
    logger.info("Executing node: reflection")

    sql_query = state.get("sql_query")
    session = state["db_connection"]
    reflections = []

    if not sql_query or not sql_query.strip().lower().startswith("select"):
        logger.warning(
            "No valid SQL query found for reflection.", sql_query=sql_query
        )
        reflections.append(
            "An error occurred during the SQL generation step. "
            "No valid SELECT query was generated."
        )
        return {"reflection": reflections, "sql_query": None}

    try:
        # Validate query using EXPLAIN
        await session.execute(text(f"EXPLAIN {sql_query}"))
        logger.info("SQL query syntax validation passed (EXPLAIN).")
    except Exception as e:
        logger.warning("SQL query syntax error", error=str(e), exc_info=True)
        reflections.append(
            f"Query syntax error: {e}. "
            f"Please check the schema again and correct it."
        )

    if not reflections:
        logger.info("Reflection result: Query is valid.")
        # Return empty reflection list to proceed to execution
        return {"reflection": []}
    else:
        logger.info(
            "Reflection result: Improvements needed.", reflections=reflections
        )
        # Clear the query so it doesn't get executed
        return {"reflection": reflections, "sql_query": None}


async def sql_executor_node(state: GraphState):
    """Executes the validated SQL query against the database."""
    sql_query = state.get("sql_query")
    logger.info("Executing node: sql_executor", sql_query=sql_query)

    if not sql_query:
        logger.error("sql_executor_node called with no query.")
        return {"execution_result": "Error: No SQL query to execute."}

    session = state["db_connection"]
    try:
        result = await session.execute(text(sql_query))
        result_dicts = [dict(row) for row in result.mappings()]
        logger.info("SQL execution successful", result_count=len(result_dicts))
        return {"execution_result": str(result_dicts)}
    except Exception as e:
        logger.error("Error during SQL execution", error=str(e), exc_info=True)
        return {"execution_result": f"Error executing query: {e}"}


async def final_answer_node(state: GraphState):
    """Generates the final answer to be shown to the user."""
    logger.info("Executing node: final_answer")
    intent = state["intent"]
    final_answer_agent = Agent("openai:gpt-4o")

    if intent == "greeting":
        answer = "Hello! How can I help you?"
    elif intent == "chit_chat":
        prompt = f"The user said: '{state['question']}'. Respond with a brief, friendly, and conversational message."
        result = await final_answer_agent.run(prompt)
        answer = result.output
    elif intent == "unknown":
        answer = "I'm sorry, I didn't understand your question. "
        "Please ask questions related to employees, departments, and salaries."
    elif state.get("execution_result"):
        if "Error" in state["execution_result"]:
            logger.error(
                "Error in query execution result",
                execution_result=state["execution_result"],
            )
            answer = "An error occurred while executing the query. "
            f"Please contact an administrator. ({state['execution_result']})"
        else:
            prompt = f"""
            Based on the following question and database query result,
            please provide a natural language answer in Korean.

            - Question: {state["question"]}
            - Query Result: {state["execution_result"]}
            """
            result = await final_answer_agent.run(prompt)
            answer = result.output
    else:
        answer = "I'm sorry, I couldn't find an answer to your question."

    logger.info("Final answer generation complete", final_answer=answer)
    return {"final_answer": answer, "is_final": True}


# --- Graph Edges and Configuration ---


def route_after_intent_classification(state: GraphState):
    """Determines the next node after intent classification."""
    intent = state["intent"]
    logger.info("Routing decision: after intent classification", intent=intent)
    if intent == "sql_generation":
        return "sql_generator"
    return "final_answer"


def route_after_reflection(state: GraphState):
    """Determines the next node after SQL reflection."""
    logger.info("Routing decision: after SQL reflection")

    # If reflection has found issues, stop and go to the final answer.
    if state.get("reflection"):
        logger.warning(
            "Reflection found issues. Halting execution.",
            reflections=state["reflection"],
        )
        return "final_answer"

    logger.info("Query is valid, routing to sql_executor")
    return "sql_executor"


# --- Graph Build ---
workflow = StateGraph(GraphState)

workflow.add_node("intent_classifier", intent_classifier_node)
workflow.add_node("sql_generator", sql_generator_node)
workflow.add_node("reflection", reflection_node)
workflow.add_node("sql_executor", sql_executor_node)
workflow.add_node("final_answer", final_answer_node)

workflow.set_entry_point("intent_classifier")

workflow.add_conditional_edges(
    "intent_classifier",
    route_after_intent_classification,
    {"sql_generator": "sql_generator", "final_answer": "final_answer"},
)
workflow.add_edge("sql_generator", "reflection")
workflow.add_conditional_edges(
    "reflection",
    route_after_reflection,
    {"final_answer": "final_answer", "sql_executor": "sql_executor"},
)
workflow.add_edge("sql_executor", "final_answer")
workflow.add_edge("final_answer", END)

# Compile the graph
agent_app = workflow.compile()
