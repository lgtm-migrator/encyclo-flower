from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional
from datetime import datetime
from models.helpers import observation_id_generator, gen_uuid, gen_image_file_name
from models.generic import Coordinates, ImageLocationText, WhatInImage
from models.custom_types import MonthHebLiteral, LocationHebLiteral


class Observation(BaseModel):
    observation_text: str
    month: Optional[MonthHebLiteral | None] = None
    location: Optional[LocationHebLiteral | None] = None


class ObservationInResponse(BaseModel):
    """
    response for added new observation.
    """

    observation_id: str


class ObservationImageMeta(ImageLocationText):
    description: str | None = None
    what_in_image: WhatInImage | None = None
    image_dt: Optional[datetime | None] = None  # TODO: set type to DateTimeHebLiteral


class ObservationImageInDB(ObservationImageMeta):
    # TODO: merge this class with QuestionImageInDB - if possible
    image_id: str = Field(default_factory=gen_uuid)
    coordinates: Coordinates = Coordinates(lat=0, lon=0, alt=0)
    orig_file_name: str = Field(default="image1.jpg")
    file_name: str | None = None
    plant_id: str | None = None
    created_dt: datetime = Field(default_factory=datetime.utcnow)
    self_link: HttpUrl | None = None
    media_link: HttpUrl | None = None
    public_url: HttpUrl | None = None

    @validator("file_name", pre=True, always=True)
    def set_file_name(cls, v, values):
        if not v:
            return gen_image_file_name(values["orig_file_name"])
        return v


class ObservationImageInDB_w_oid(BaseModel):
    observation_id: str
    image: ObservationImageMeta


class ObservationInDB(Observation):
    observation_id: str = Field(default_factory=observation_id_generator)
    images: List[Optional[ObservationImageInDB]] = []  # TODO: add image class
    comments: List = []  # TODO: add comment class
    user_id: str
    created_dt: datetime = Field(default_factory=datetime.utcnow)
    submitted: bool = False
    deleted: bool = False
