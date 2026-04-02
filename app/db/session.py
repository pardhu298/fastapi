from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Async SQLAlchemy engine for PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL, echo=settings.DEBUG, future=True
)

# Session factory for dependency injection
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
