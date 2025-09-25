import asyncio
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db_session
from src.database.utils import get_db_schema
from src.schemas.agent_schemas import GraphState
from src.schemas.api_schemas import QueryRequest
from src.services.text_to_sql_agent import agent_app

# 로거 설정
logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/agent/invoke")
async def invoke_agent(
    request: QueryRequest, db_session: AsyncSession = Depends(get_db_session)
):
    """Text-to-SQL 에이전트를 스트리밍 방식으로 실행합니다."""
    if not request.question:
        logger.warning("사용자가 질문 없이 요청을 보냈습니다.")
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    logger.info("에이전트 스트리밍 호출 시작", question=request.question)

    async def stream_generator():
        try:
            schema = await get_db_schema(db_session)
            initial_state: GraphState = {
                "question": request.question,
                "db_schema": schema,
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

            async for event in agent_app.astream_events(
                initial_state, version="v1"
            ):
                kind = event["event"]
                if kind == "on_chain_end":
                    if event["name"] == "sql_generator":
                        data = event["data"]["output"]
                        if thoughts := data.get("thoughts"):
                            # 스트림으로 생각(thought) 전송
                            yield f"data: {json.dumps({'type': 'thought', 'data': thoughts[-1]})}\n\n"  # noqa: E501
                            await asyncio.sleep(
                                0.01
                            )  # 클라이언트가 받을 수 있도록 잠시 대기

                    elif event["name"] == "final_answer":
                        data = event["data"]["output"]
                        if final_answer := data.get("final_answer"):
                            # 스트림으로 최종 답변(final_answer) 전송
                            yield f"data: {json.dumps({'type': 'answer', 'data': final_answer})}\n\n"  # noqa: E501
                            await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(
                "에이전트 스트리밍 중 오류 발생", error=str(e), exc_info=True
            )
            error_message = json.dumps(
                {"type": "error", "data": f"An error occurred: {e}"}
            )
            yield f"data: {error_message}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.get("/")
def read_root():
    return {
        "message": "Text-to-SQL Agent is running. "
        "Use the /docs endpoint for API details."
    }
