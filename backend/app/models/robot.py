from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RobotStatus(Base):
    __tablename__ = "robot_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(50), default="idle")  # idle | navigating | charging
    battery: Mapped[float] = mapped_column(Float, default=100.0)
    current_hall_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("halls.id"), nullable=True)
    current_x: Mapped[float] = mapped_column(Float, default=0.0)
    current_y: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class NavigationRequest(Base):
    __tablename__ = "navigation_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_exhibit_id: Mapped[int] = mapped_column(Integer, ForeignKey("exhibits.id"))
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending | in_progress | completed | cancelled
    estimated_time: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
