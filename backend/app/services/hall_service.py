from sqlalchemy.orm import Session

from app.models.hall import Hall
from app.schemas.hall import HallLocalized


class HallService:
    @staticmethod
    def list_halls(db: Session, lang: str) -> list[HallLocalized]:
        halls = db.query(Hall).all()
        return [
            HallLocalized(
                id=h.id,
                name=getattr(h, f"name_{lang}") or h.name_en,
                floor_number=h.floor_number,
                description=h.description,
                map_image_url=h.map_image_url,
                language=lang,
            )
            for h in halls
        ]
