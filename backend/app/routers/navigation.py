from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.robot import NavigationStartRequest, NavigationRequestOut
from app.services.navigation_service import NavigationService

router = APIRouter()


@router.post("/start", response_model=NavigationRequestOut)
def start_navigation(payload: NavigationStartRequest, db: Session = Depends(get_db)):
    return NavigationService.start(db, payload.exhibit_id)


@router.post("/stop")
def stop_navigation(db: Session = Depends(get_db)):
    return NavigationService.stop(db)


@router.get("/status", response_model=NavigationRequestOut | None)
def navigation_status(db: Session = Depends(get_db)):
    return NavigationService.current_status(db)
