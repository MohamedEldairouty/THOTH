from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.map_service import MapService

router = APIRouter()


@router.get("/")
def get_map(db: Session = Depends(get_db)):
    return MapService.get_map_overview(db)


@router.get("/exhibits")
def get_map_exhibits(
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    return MapService.get_exhibit_positions(db, lang)


@router.get("/route")
def get_route(
    from_exhibit: int | None = None,
    to_exhibit: int = Query(...),
    db: Session = Depends(get_db),
):
    return MapService.get_route(db, from_exhibit, to_exhibit)
