from datetime import datetime
from sqlalchemy import Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NavigationRequest(Base):
    __tablename__ = "navigation_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_exhibit_id: Mapped[int] = mapped_column(Integer, ForeignKey("exhibits.id"))
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending | in_progress | arrived | cancelled
    estimated_time: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
