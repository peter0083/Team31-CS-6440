"""Database models and session management for MS3 microservice."""

from datetime import date, datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import TIMESTAMP, Date, Double, Index, Integer, String, Text, text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.ms3.ms3_config import settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""

    pass


class PatientDB(Base):
    """Database model for storing patient data."""

    __tablename__ = "patient"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    race: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ethnicity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    marital_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class ConditionDB(Base):
    """Database model for storing condition data."""

    __tablename__ = "condition"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    subject_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    code_system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    onset_date_time: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    clinical_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (Index("idx_condition_subject_id", "subject_id"),)


class ObservationDB(Base):
    """Database model for storing observation (lab result) data."""

    __tablename__ = "observation"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    subject_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    code_system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_quantity_value: Mapped[Optional[float]] = mapped_column(
        Double, nullable=True
    )
    value_quantity_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    effective_date_time: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, nullable=True
    )
    reference_range_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (Index("idx_observation_subject_id", "subject_id"),)


class MedicationRequestDB(Base):
    """Database model for storing medication request data."""

    __tablename__ = "medicationrequest"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    subject_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    medication_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generic_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dose_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    frequency_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    authored_on: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (Index("idx_medicationrequest_subject_id", "subject_id"),)


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

