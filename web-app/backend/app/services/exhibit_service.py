from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.exhibit import Exhibit
from app.schemas.exhibit import ExhibitCreate, ExhibitUpdate, ExhibitLocalized


def _localize(exhibit: Exhibit, lang: str) -> ExhibitLocalized:
    """Map multilingual DB row to the single-language schema the frontend expects."""
    return ExhibitLocalized(
        id=exhibit.id,
        title=getattr(exhibit, f"title_{lang}") or exhibit.title_en,
        short_description=getattr(exhibit, f"short_description_{lang}"),
        full_description=getattr(exhibit, f"full_description_{lang}"),
        era=exhibit.era,
        category_id=exhibit.category_id,
        hall_id=exhibit.hall_id,
        image_url=exhibit.image_url,
        video_url=exhibit.video_url,
        audio_url=getattr(exhibit, f"audio_{lang}_url"),
        x_position=exhibit.x_position,
        y_position=exhibit.y_position,
        language=lang,
        created_at=exhibit.created_at,
        updated_at=exhibit.updated_at,
    )


class ExhibitService:
    @staticmethod
    def list_exhibits(
        db: Session,
        lang: str,
        category_id: int | None,
        hall_id: int | None,
        era: str | None,
        search: str | None,
    ) -> list[ExhibitLocalized]:
        q = db.query(Exhibit)
        if category_id:
            q = q.filter(Exhibit.category_id == category_id)
        if hall_id:
            q = q.filter(Exhibit.hall_id == hall_id)
        if era:
            q = q.filter(Exhibit.era == era)
        if search:
            q = q.filter(
                or_(
                    Exhibit.title_en.ilike(f"%{search}%"),
                    Exhibit.title_ar.ilike(f"%{search}%"),
                    Exhibit.title_fr.ilike(f"%{search}%"),
                )
            )
        return [_localize(e, lang) for e in q.all()]

    @staticmethod
    def get_exhibit(db: Session, exhibit_id: int, lang: str) -> ExhibitLocalized | None:
        exhibit = db.query(Exhibit).filter(Exhibit.id == exhibit_id).first()
        if not exhibit:
            return None
        return _localize(exhibit, lang)

    @staticmethod
    def create_exhibit(db: Session, payload: ExhibitCreate) -> Exhibit:
        exhibit = Exhibit(**payload.model_dump())
        db.add(exhibit)
        db.commit()
        db.refresh(exhibit)
        return exhibit

    @staticmethod
    def update_exhibit(db: Session, exhibit_id: int, payload: ExhibitUpdate) -> Exhibit | None:
        exhibit = db.query(Exhibit).filter(Exhibit.id == exhibit_id).first()
        if not exhibit:
            return None
        for key, value in payload.model_dump().items():
            setattr(exhibit, key, value)
        db.commit()
        db.refresh(exhibit)
        return exhibit

    @staticmethod
    def delete_exhibit(db: Session, exhibit_id: int) -> bool:
        exhibit = db.query(Exhibit).filter(Exhibit.id == exhibit_id).first()
        if not exhibit:
            return False
        db.delete(exhibit)
        db.commit()
        return True
