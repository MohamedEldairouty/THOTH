from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.exhibit import ExhibitCreate, ExhibitDB, ExhibitLocalized, ExhibitUpdate
from app.services.exhibit_service import ExhibitService

router = APIRouter()


@router.get("", response_model=list[ExhibitLocalized])
def list_exhibits(
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    category_id: int | None = None,
    hall_id: int | None = None,
    era: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    return ExhibitService.list_exhibits(db, lang, category_id, hall_id, era, search)


@router.get("/{exhibit_id}", response_model=ExhibitLocalized)
def get_exhibit(
    exhibit_id: int,
    lang: str = Query("en", pattern="^(en|ar|fr)$"),
    db: Session = Depends(get_db),
):
    exhibit = ExhibitService.get_exhibit(db, exhibit_id, lang)
    if not exhibit:
        raise HTTPException(status_code=404, detail="Exhibit not found")
    return exhibit


@router.post("", response_model=ExhibitDB, status_code=201)
def create_exhibit(payload: ExhibitCreate, db: Session = Depends(get_db)):
    return ExhibitService.create_exhibit(db, payload)


@router.put("/{exhibit_id}", response_model=ExhibitDB)
def update_exhibit(exhibit_id: int, payload: ExhibitUpdate, db: Session = Depends(get_db)):
    exhibit = ExhibitService.update_exhibit(db, exhibit_id, payload)
    if not exhibit:
        raise HTTPException(status_code=404, detail="Exhibit not found")
    return exhibit


@router.delete("/{exhibit_id}", status_code=204)
def delete_exhibit(exhibit_id: int, db: Session = Depends(get_db)):
    if not ExhibitService.delete_exhibit(db, exhibit_id):
        raise HTTPException(status_code=404, detail="Exhibit not found")
