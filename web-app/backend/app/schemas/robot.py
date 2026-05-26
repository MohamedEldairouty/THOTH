from datetime import datetime
from pydantic import BaseModel


class RobotStatusOut(BaseModel):
    """Live pose + status from the ROS bridge — not persisted."""
    status: str
    current_x: float
    current_y: float


class NavigationStartRequest(BaseModel):
    exhibit_id: int


class NavigationRequestOut(BaseModel):
    id: int
    target_exhibit_id: int
    status: str
    estimated_time: int | None
    created_at: datetime
    model_config = {"from_attributes": True}
