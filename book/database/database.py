from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from config_data.config import settings


DATABASE_URL = (f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
                f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
                f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
                )

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)
