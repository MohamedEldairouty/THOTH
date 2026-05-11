from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Hall(Base):
    __tablename__ = "halls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_en: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str] = mapped_column(String(100))
    name_fr: Mapped[str] = mapped_column(String(100))
    floor_number: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    map_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    exhibits: Mapped[list["Exhibit"]] = relationship(back_populates="hall")
