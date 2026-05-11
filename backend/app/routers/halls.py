from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.hall import HallLocalized
from app.services.hall_service import HallService

router = APIRouter()


@router.get("/", response_model=list[HallLocalized])
def list_halls(
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    return HallService.list_halls(db, lang)
