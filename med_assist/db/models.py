"""SQLAlchemy 2.0 declarative models — mirror of db/schema.sql."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(16))
    is_pregnant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pregnancy_due_date: Mapped[date | None] = mapped_column(Date)
    allergies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    conditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    medications: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    onboarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("age IS NULL OR (age >= 0 AND age <= 120)", name="age_range"),
        CheckConstraint("gender IS NULL OR gender IN ('male','female','other')", name="gender_enum"),
    )


class CabinetItem(Base):
    __tablename__ = "cabinet_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    generic_name: Mapped[str | None] = mapped_column(Text)
    dosage: Mapped[str | None] = mapped_column(Text)
    item_type: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    added_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
