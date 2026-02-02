from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class LocationObj(BaseModel):
    lat: float
    lon: float
    alt_m: float = 0
    place: Optional[str] = None


LocationInput = Union[str, LocationObj]


ChartType = Literal["natal", "moment", "solar_arc", "secondary_progression"]


class Metadata(BaseModel):
    chart_type: ChartType
    timestamp_utc: Optional[str] = None
    location: Optional[LocationInput] = None
    client_name: Optional[str] = None
    solar_arc_sun: Optional[Literal["mean", "true"]] = None


class Settings(BaseModel):
    house_system: str = Field(default="placidus")
    zodiac: str = Field(default="tropical")
    coordinate_system: str = Field(default="ecliptic")


class ChartRequest(BaseModel):
    metadata: Metadata
    settings: Optional[Settings] = None
    frame_a: Optional["ChartRequest"] = None


class ChartFrameRequest(BaseModel):
    metadata: Metadata
    settings: Optional[Settings] = None


TransitType = Literal[
    "transit",
    "synastry",
    "astrocartography",
    "solar_arc",
    "secondary_progression",
    "lunations",
]


class TransitMetadata(BaseModel):
    transit_type: TransitType
    timestamp_utc: Optional[str] = None
    location: Optional[LocationInput] = None
    solar_arc_sun: Optional[Literal["mean", "true"]] = None
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None
    lunation_type: Optional[str] = None
    eclipse_kind: Optional[str] = None


class TransitRequest(BaseModel):
    metadata: TransitMetadata
    frame_a: Optional[ChartFrameRequest] = None
    frame_b: Optional[ChartFrameRequest] = None


TimelineType = Literal["transit", "secondary_progression", "solar_arc"]


class TimelineMetadata(BaseModel):
    start_utc: str
    end_utc: str
    timeline_type: TimelineType = "transit"
    bodies: Optional[list[str]] = None


class TimelineRequest(BaseModel):
    metadata: TimelineMetadata
    frame_a: ChartFrameRequest
    settings: Optional[Settings] = None


ChartRequest.model_rebuild()
