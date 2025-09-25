import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
from src.database.utils import get_db_schema
from src.schemas.agent_schemas import GraphState
from src.schemas.api_schemas import QueryRequest, QueryResponse
from src.services.text_to_sql_agent import agent_app

# 로거 설정
logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/agent/invoke", response_model=QueryResponse)
async def invoke_agent(
    request: QueryRequest, db_session: AsyncSession = Depends(get_db_session)
):
    """Text-to-SQL 에이전트를 비동기적으로 실행합니다."""
    if not request.question:
        logger.warning("사용자가 질문 없이 요청을 보냈습니다.")
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    logger.info("에이전트 호출 시작", question=request.question)

    try:
        schema = await get_db_schema(db_session)

        initial_state: GraphState = {
            "question": request.question,
            "db_schema": schema,
            "db_connection": db_session,
            "reflection_history": [],
            "intent": None,
            "sql_query": None,
            "reflection": [],
            "execution_result": None,
            "final_answer": None,
            "messages": [],
            "thoughts": [],
            "is_final": False,
        }

        final_state = await agent_app.ainvoke(initial_state)

        answer = final_state.get(
            "final_answer", "죄송합니다, 답변을 생성하지 못했습니다."
        )
        thoughts = final_state.get("thoughts", [])
        logger.info("에이전트 호출 완료", final_answer=answer, thoughts=thoughts)
        return {"answer": answer, "thoughts": thoughts}

    except Exception as e:
        logger.error(
            "에이전트 실행 중 심각한 오류 발생",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {e}"
        ) from e


@router.get("/")
def read_root():
    return {
        "message": "Text-to-SQL Agent is running. "
        "Use the /docs endpoint for API details."
    }
