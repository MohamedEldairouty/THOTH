"""
Tour models: a Tour is a curated or custom sequence of exhibits.
A TourRun is one execution of a tour by the robot.

Status flow for a TourRun:
    pending  → robot has the goal, hasn't started moving yet
    moving   → traveling to current_stop_index
    arrived  → robot reached the exhibit, waiting for "Continue"
    completed → reached the final exhibit
    cancelled → user cancelled
"""
from datetime import datetime
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tour(Base):
    __tablename__ = "tours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name_en: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str] = mapped_column(String(100))
    name_fr: Mapped[str] = mapped_column(String(100))

    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_fr: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Curated tours come from seed data; custom tours are user-built one-offs.
    is_preset: Mapped[bool] = mapped_column(Boolean, default=True)

    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    stops: Mapped[list["TourStop"]] = relationship(
        back_populates="tour",
        cascade="all, delete-orphan",
        order_by="TourStop.sequence_order",
    )


class TourStop(Base):
    __tablename__ = "tour_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tour_id: Mapped[int] = mapped_column(Integer, ForeignKey("tours.id", ondelete="CASCADE"))
    exhibit_id: Mapped[int] = mapped_column(Integer, ForeignKey("exhibits.id"))
    sequence_order: Mapped[int] = mapped_column(Integer)

    tour: Mapped["Tour"] = relationship(back_populates="stops")


class TourRun(Base):
    __tablename__ = "tour_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tour_id: Mapped[int] = mapped_column(Integer, ForeignKey("tours.id"))

    # 0-based index into the tour's stops list
    current_stop_index: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | moving | arrived | completed | cancelled

    language: Mapped[str] = mapped_column(String(10), default="en")

    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
