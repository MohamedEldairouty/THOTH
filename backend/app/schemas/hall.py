from pydantic import BaseModel


class HallBase(BaseModel):
    name_en: str
    name_ar: str
    name_fr: str
    floor_number: int = 1
    description: str | None = None
    map_image_url: str | None = None


class HallCreate(HallBase):
    pass


class HallDB(HallBase):
    id: int
    model_config = {"from_attributes": True}


class HallLocalized(BaseModel):
    id: int
    name: str
    floor_number: int
    description: str | None
    map_image_url: str | None
    language: str
    model_config = {"from_attributes": True}
