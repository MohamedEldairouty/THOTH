from datetime import datetime
from pydantic import BaseModel


class ExhibitBase(BaseModel):
    title_en: str
    title_ar: str
    title_fr: str
    short_description_en: str | None = None
    short_description_ar: str | None = None
    short_description_fr: str | None = None
    full_description_en: str | None = None
    full_description_ar: str | None = None
    full_description_fr: str | None = None
    era: str | None = None
    category_id: int | None = None
    hall_id: int | None = None
    image_url: str | None = None
    video_url: str | None = None
    audio_en_url: str | None = None
    audio_ar_url: str | None = None
    audio_fr_url: str | None = None
    x_position: float | None = None
    y_position: float | None = None


class ExhibitCreate(ExhibitBase):
    pass


class ExhibitUpdate(ExhibitBase):
    pass


class ExhibitDB(ExhibitBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExhibitLocalized(BaseModel):
    """What the frontend receives — language already resolved by backend."""
    id: int
    title: str
    short_description: str | None
    full_description: str | None
    era: str | None
    category_id: int | None
    hall_id: int | None
    image_url: str | None
    video_url: str | None
    audio_url: str | None
    x_position: float | None
    y_position: float | None
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
