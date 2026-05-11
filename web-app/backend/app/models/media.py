from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exhibit_id: Mapped[int] = mapped_column(Integer, ForeignKey("exhibits.id", ondelete="CASCADE"))
    media_type: Mapped[str] = mapped_column(String(50))  # image | video | audio
    url: Mapped[str] = mapped_column(String(500))

    caption_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_ar: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption_fr: Mapped[str | None] = mapped_column(Text, nullable=True)

    exhibit: Mapped["Exhibit"] = relationship(back_populates="media")
