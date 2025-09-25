from typing import Any, List, Literal, Sequence, TypedDict, Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession


class ThoughtAndSQL(BaseModel):
    """
    SQL 쿼리 생성을 위한 생각과 SQL 쿼리 모델.
    """
    thought: str = Field(description="SQL 쿼리 생성을 위한 논리적 사고 과정")
    query: str = Field(
        description="사용자의 질문에 답하기 위한 PostgreSQL SELECT 쿼리문",
        pattern=r"^SELECT.*",
    )


class Intent(BaseModel):
    """
    사용자의 질문 의도 분류 모델.
    """

    intent: Literal["sql_generation", "greeting", "chit_chat", "unknown"] = Field(
        ...,
        description="""사용자 질문의 의도.
- sql_generation: 데이터베이스에서 정보를 조회해야 하는 질문.
- greeting: 간단한 인사 또는 감사 표현.
- chit_chat: 일반적인 대화 또는 잡담.
- unknown: 위 분류에 해당하지 않는 모든 질문.
""",
    )


class GraphState(TypedDict):
    """Represents the state of our graph."""

    question: str
    db_schema: str
    intent: str | None
    sql_query: str | None
    reflection: List[str]
    reflection_history: List[str]
    execution_result: str | None
    final_answer: str | None
    messages: Annotated[Sequence[BaseMessage], add_messages]
    thoughts: List[str]
    is_final: bool
