from datetime import datetime
from sqlalchemy import Integer, String, Text, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Exhibit(Base):
    __tablename__ = "exhibits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title_en: Mapped[str] = mapped_column(String(200))
    title_ar: Mapped[str] = mapped_column(String(200))
    title_fr: Mapped[str] = mapped_column(String(200))

    short_description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description_fr: Mapped[str | None] = mapped_column(Text, nullable=True)

    full_description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_description_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_description_fr: Mapped[str | None] = mapped_column(Text, nullable=True)

    era: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    hall_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("halls.id"), nullable=True)

    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_en_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_ar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_fr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    x_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_position: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    category: Mapped["Category"] = relationship(back_populates="exhibits")
    hall: Mapped["Hall"] = relationship(back_populates="exhibits")
    media: Mapped[list["Media"]] = relationship(back_populates="exhibit")
