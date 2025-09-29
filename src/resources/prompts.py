"""This module contains all the LLM prompts used in the application."""


class Prompts:
    """A container for all application prompts, structured as static methods."""

    @staticmethod
    def classify_intent(question: str) -> str:
        """Generates the prompt for the intent classification node."""
        return f"""
    Classify the user's intent based on their question into one of
    the following categories:
        "sql_generation", "greeting", "chit_chat", or "unknown".

    - For work-related questions involving data lookup or analysis,
        classify as "sql_generation".
    - If the intent is unclear, you must classify it as "unknown".

    User Question: {question}
    """

    @staticmethod
    def generate_sql(
        db_schema: str, reflection_feedback: str, question: str
    ) -> str:
        """Generates the prompt for the SQL generation node."""
        return f"""
    You are a PostgreSQL database expert.
    Your goal is to generate a SQL query to answer the user's question.
    First, think about the user's question and the database schema
    to devise a plan.
    Then, generate the SQL query based on your plan.

    ### Database Schema:
    {db_schema}

    ### Feedback from previous attempts (if any):
    {reflection_feedback}

    ### User Question:
    {question}

    The final query must be a single, valid PostgreSQL SELECT statement ending
    with a semicolon.
    """

    @staticmethod
    def synthesize_result(question: str, execution_result: str) -> str:
        """Generates the prompt for the result synthesis node."""
        return f"""
        Based on the user's question and the database query result,
        synthesize a thought process in **Korean**.
        This thought process should explain how the data answers
        the user's question,
        and it will be shown to the user.

        **You must answer based only on the provided SQL execution results.**

        - User Question: {question}
        - Query Result: {execution_result}

        Your thought process must be in clear, natural **Korean**.
        """

    @staticmethod
    def generate_chit_chat(question: str) -> str:
        """Generates the prompt for a chit-chat response."""
        return f"""The user said: '{question}'.
        Respond with a brief, friendly, and conversational message."""

    @staticmethod
    def generate_final_answer(thought: str, question: str) -> str:
        """Generates the prompt for the final answer node."""
        return f"""
        Based on the following thought process (which is already in Korean),
        provide a final, polished, and natural-language answer in Korean.
        The thought process is for your reference,
        but the final answer should be a concise and clear response
        to the user's original question.

        **You must answer based only on the provided SQL execution results.**

        - Thought (in Korean): {thought}
        - Original Question: {question}

        **Final Answer (in Korean):**
        """
