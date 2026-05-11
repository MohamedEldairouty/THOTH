from datetime import datetime
from pydantic import BaseModel


class RobotStatusOut(BaseModel):
    id: int
    status: str
    battery: float
    current_hall_id: int | None
    current_x: float
    current_y: float
    updated_at: datetime
    model_config = {"from_attributes": True}


class NavigationStartRequest(BaseModel):
    exhibit_id: int


class NavigationRequestOut(BaseModel):
    id: int
    target_exhibit_id: int
    status: str
    estimated_time: int | None
    created_at: datetime
    model_config = {"from_attributes": True}
