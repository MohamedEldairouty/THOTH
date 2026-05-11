from pydantic import BaseModel


class CategoryBase(BaseModel):
    name_en: str
    name_ar: str
    name_fr: str


class CategoryCreate(CategoryBase):
    pass


class CategoryDB(CategoryBase):
    id: int
    model_config = {"from_attributes": True}


class CategoryLocalized(BaseModel):
    id: int
    name: str
    language: str
    model_config = {"from_attributes": True}
