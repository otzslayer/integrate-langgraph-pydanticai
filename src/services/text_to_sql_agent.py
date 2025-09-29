import structlog
from langgraph.graph import END, StateGraph
from pydantic_ai import Agent
from sqlalchemy import text

from src.database.connection import AsyncSessionLocal
from src.resources.prompts import Prompts
from src.schemas.agent_schemas import GraphState, Intent, ThoughtAndSQL

# 로거 설정
logger = structlog.get_logger(__name__)

# --- Agent Nodes ---


async def intent_classifier_node(state: GraphState):
    """Classifies the user's question intent using an LLM agent."""
    logger.info("Executing node: intent_classifier")

    intent_agent = Agent("openai:gpt-4o", output_type=Intent)
    prompt = Prompts.classify_intent(state["question"])

    try:
        result = await intent_agent.run(prompt)
        intent = result.output.intent
        logger.info("Intent classification complete", intent=intent)
    except Exception as e:
        logger.error(
            "Error during intent classification", error=str(e), exc_info=True
        )
        intent = "unknown"

    # Initialize thought_history list
    return {"intent": intent, "thought_history": [], "messages": []}


async def sql_generator_node(state: GraphState):
    """Generates a SQL query and a thought about it."""
    logger.info("Executing node: sql_generator")

    reflection_feedback = "\n".join(state.get("reflection", []))
    prompt = Prompts.generate_sql(
        db_schema=state["db_schema"],
        reflection_feedback=reflection_feedback
        if reflection_feedback
        else "None",
        question=state["question"],
    )

    sql_agent = Agent("openai:gpt-4o", output_type=ThoughtAndSQL)

    try:
        result = await sql_agent.run(prompt)
        thought = result.output.thought
        sql_query = result.output.query

        logger.info(
            "SQL generation successful", thought=thought, sql_query=sql_query
        )

        # Add thought to state
        thought_history = state.get("thought_history", []) + [thought]

        return {"thought_history": thought_history, "sql_query": sql_query}

    except Exception as e:
        logger.error("Error during SQL generation", error=str(e), exc_info=True)
        # Set reflection to indicate error and route to final_answer
        return {"reflection": [f"Error during SQL generation: {e}"]}


async def reflection_node(state: GraphState):
    """Validates the generated SQL query and suggests improvements."""
    logger.info("Executing node: reflection")

    sql_query = state.get("sql_query")
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

    async with AsyncSessionLocal() as session:
        try:
            # Validate query using EXPLAIN
            await session.execute(text(f"EXPLAIN {sql_query}"))
            logger.info("SQL query syntax validation passed (EXPLAIN).")
        except Exception as e:
            logger.warning(
                "SQL query syntax error", error=str(e), exc_info=True
            )
            reflections.append(
                f"Query syntax error: {e}. "
                f"Please check the schema again and correct it."
            )

    if not reflections:
        logger.info("Reflection result: Query is valid.")
        return {"reflection": []}
    else:
        logger.info(
            "Reflection result: Improvements needed.", reflections=reflections
        )
        return {"reflection": reflections, "sql_query": None}


async def sql_executor_node(state: GraphState):
    """Executes the validated SQL query against the database."""
    sql_query = state.get("sql_query")
    logger.info("Executing node: sql_executor", sql_query=sql_query)

    if not sql_query:
        logger.error("sql_executor_node called with no query.")
        return {"execution_result": "Error: No SQL query to execute."}

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text(sql_query))
            result_dicts = [dict(row) for row in result.mappings()]
            logger.info(
                "SQL execution successful", result_count=len(result_dicts)
            )
            return {"execution_result": str(result_dicts)}
        except Exception as e:
            logger.error(
                "Error during SQL execution", error=str(e), exc_info=True
            )
            return {"execution_result": f"Error executing query: {e}"}


async def synthesize_result_node(state: GraphState):
    """
    Synthesizes the SQL execution result into a natural language thought
    before generating the final answer.
    """
    logger.info("Executing node: synthesize_result")

    if (
        state.get("execution_result")
        and "Error" not in state["execution_result"]
    ):
        prompt = Prompts.synthesize_result(
            question=state["question"],
            execution_result=state["execution_result"],
        )
        thought_agent = Agent("openai:gpt-4o")
        try:
            result = await thought_agent.run(prompt)
            thought = result.output
            logger.info("Result synthesis successful.", thought=thought)
            return {"thought": thought}
        except Exception as e:
            logger.error(
                "Error during result synthesis", error=str(e), exc_info=True
            )
            return {"thought": f"Error during result synthesis: {e}"}
    elif state.get("reflection"):
        thought = (
            "An error occurred during the SQL generation or reflection phase. "
            f"The error was: {state['reflection']}"
        )
        return {"thought": thought}
    else:
        thought = (
            "No execution result was found, so I cannot provide an answer."
        )
        return {"thought": thought}


async def final_answer_node(state: GraphState):
    """Generates the final answer to be shown to the user."""
    logger.info("Executing node: final_answer")
    intent = state["intent"]
    final_answer_agent = Agent("openai:gpt-4o")

    if intent == "greeting":
        answer = "Hello! How can I help you?"
    elif intent == "chit_chat":
        prompt = Prompts.generate_chit_chat(state["question"])
        result = await final_answer_agent.run(prompt)
        answer = result.output
    elif intent == "unknown":
        answer = "I'm sorry, I didn't understand your question. "
        "Please ask questions related to employees, departments, and salaries."
    elif state.get("thought"):
        prompt = Prompts.generate_final_answer(
            thought=state["thought"], question=state["question"]
        )
        result = await final_answer_agent.run(prompt)
        answer = result.output
    else:
        answer = "I'm sorry, I couldn't find an answer to your question."

    logger.info("Final answer generation complete", final_answer=answer)
    return {"answer": answer, "is_final": True}


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
            "Reflection found issues. "
            "Halting execution and synthesizing result.",
            reflections=state["reflection"],
        )
        return "synthesize_result"

    logger.info("Query is valid, routing to sql_executor")
    return "sql_executor"


# --- Graph Build ---
workflow = StateGraph(GraphState)

workflow.add_node("intent_classifier", intent_classifier_node)
workflow.add_node("sql_generator", sql_generator_node)
workflow.add_node("reflection", reflection_node)
workflow.add_node("sql_executor", sql_executor_node)
workflow.add_node("synthesize_result", synthesize_result_node)
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
    # If reflection fails, it now goes to synthesize, not directly to the end.
    {"final_answer": "synthesize_result", "sql_executor": "sql_executor"},
)
workflow.add_edge("sql_executor", "synthesize_result")
workflow.add_edge("synthesize_result", "final_answer")
workflow.add_edge("final_answer", END)

# Compile the graph
agent_app = workflow.compile()
