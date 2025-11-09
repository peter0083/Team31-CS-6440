"""Database models and session management for MS2 microservice."""

from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import JSON, Column, DateTime, Float, Index, Integer, String, text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.ms2.ms2_config import settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""

    pass


class ParsedCriteriaDB(Base):
    """Database model for storing parsed criteria."""

    __tablename__ = "parsed_criteria"

    nct_id = Column(String(20), primary_key=True, index=True)
    parsing_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    inclusion_criteria = Column(JSON, nullable=False)
    exclusion_criteria = Column(JSON, nullable=False)
    parsing_confidence = Column(Float, nullable=False, index=True)
    total_rules_extracted = Column(Integer, nullable=False)
    model_used = Column(String(50), nullable=False)
    reasoning_steps = Column(JSON, nullable=True)
    raw_input = Column(JSON, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(50), default="openai")  # 'csv_import' or 'openai'

    __table_args__ = (
        Index('idx_confidence_timestamp', 'parsing_confidence', 'parsing_timestamp'),
    )


# Database engine and session
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # Test connections before using
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


async def check_db_connection() -> bool:
    """Check if database is connected."""
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
