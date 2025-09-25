import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

# 전역 예외 핸들러 설정
# 이 코드는 다른 모듈보다 먼저 실행되어야 합니다.
from src.core.custom_logging import handle_uncaught_exception

sys.excepthook = handle_uncaught_exception

from src.api.endpoints import router
from src.database.connection import lifespan

load_dotenv()

app = FastAPI(
    title="Text-to-SQL Multi-Agent (SQLAlchemy)",
    description="Pydantic AI와 LangGraph v1.0.0을 SQLAlchemy 기반으로 "
    "리팩토링한 Text-to-SQL 에이전트",
    lifespan=lifespan,
)

app.include_router(router)


if __name__ == "__main__":
    # 이 블록은 uvicorn으로 직접 실행될 때 사용됩니다.
    # 예: python main.py
    # 프로덕션 환경에서는 gunicorn/uvicorn 워커로 실행되므로, 이 블록은 실행되지 않습니다.
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
