import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 로거 설정
logger = structlog.get_logger(__name__)

DATABASE_URL = "postgresql+asyncpg://myuser:mypassword@localhost:5432/text2sql"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """FastAPI 앱의 라이프사이클 동안 DB 엔진을 관리합니다."""
    logger.info("🚀 애플리케이션 시작")
    yield
    logger.info("🏁 애플리케이션 종료, DB 엔진 연결 해제")
    await engine.dispose()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성 주입을 통해 DB 세션을 제공합니다."""
    async with AsyncSessionLocal() as session:
        yield session
