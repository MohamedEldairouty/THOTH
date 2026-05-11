from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.category import CategoryLocalized
from app.services.category_service import CategoryService

router = APIRouter()


@router.get("/", response_model=list[CategoryLocalized])
def list_categories(
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    return CategoryService.list_categories(db, lang)
