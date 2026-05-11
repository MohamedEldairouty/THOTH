from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryLocalized


class CategoryService:
    @staticmethod
    def list_categories(db: Session, lang: str) -> list[CategoryLocalized]:
        categories = db.query(Category).all()
        return [
            CategoryLocalized(
                id=c.id,
                name=getattr(c, f"name_{lang}") or c.name_en,
                language=lang,
            )
            for c in categories
        ]
