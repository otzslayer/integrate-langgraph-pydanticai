import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 로거 설정
logger = structlog.get_logger(__name__)


async def get_db_schema(session: AsyncSession) -> str:
    """데이터베이스 스키마를 조회합니다."""
    logger.info("데이터베이스 스키마 조회 시작")
    async with session.begin():
        try:
            result = await session.execute(
                text("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """)
            )
            rows = result.fetchall()

            schema_dict = {}
            for row in rows:
                table = row[0]  # table_name
                if table not in schema_dict:
                    schema_dict[table] = []
                schema_dict[table].append(
                    f"{row[1]} {row[2]}"
                )  # column_name data_type

            schema_str = ""
            for table, columns in schema_dict.items():
                schema_str += f"Table {table}:\n"
                for col in columns:
                    schema_str += f"  - {col}\n"

            logger.info("데이터베이스 스키마 조회 성공", tables=list(schema_dict.keys()))
            return schema_str
        except Exception as e:
            logger.error("데이터베이스 스키마 조회 중 오류 발생", error=str(e), exc_info=True)
            raise
