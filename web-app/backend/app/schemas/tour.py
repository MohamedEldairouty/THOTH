from datetime import datetime
from pydantic import BaseModel


class TourStopOut(BaseModel):
    sequence_order: int
    exhibit_id: int
    exhibit_title: str
    exhibit_image: str | None
    x_position: float | None
    y_position: float | None


class TourSummary(BaseModel):
    id: int
    name: str
    description: str | None
    estimated_minutes: int | None
    is_preset: bool
    stop_count: int
    language: str


class TourDetail(TourSummary):
    stops: list[TourStopOut]


class TourRunOut(BaseModel):
    id: int
    tour_id: int
    tour_name: str
    current_stop_index: int
    total_stops: int
    status: str   # pending | moving | arrived | completed | cancelled
    language: str

    current_exhibit_id: int | None
    current_exhibit_title: str | None
    current_exhibit_image: str | None
    target_x: float | None
    target_y: float | None

    next_exhibit_id: int | None
    next_exhibit_title: str | None

    started_at: datetime
    ended_at: datetime | None


class StartTourRequest(BaseModel):
    tour_id: int | None = None       # use a preset tour
    exhibit_ids: list[int] | None = None  # OR build a custom tour
    language: str = "en"
