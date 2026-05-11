from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.robot import RobotStatusOut
from app.services.robot_service import RobotService

router = APIRouter()


@router.get("/status", response_model=RobotStatusOut)
def get_robot_status(db: Session = Depends(get_db)):
    return RobotService.get_status(db)
