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
    name: Optional[str] = None
    solar_arc_sun: Optional[Literal["mean", "true"]] = None


class PointsSettings(BaseModel):
    lilith: Optional[Literal["mean", "true"]] = None


class Settings(BaseModel):
    house_system: str = Field(default="placidus")
    zodiac: str = Field(default="tropical")
    coordinate_system: str = Field(default="ecliptic")
    points: Optional[PointsSettings] = None


class Subject(BaseModel):
    name: Optional[str] = None


class ChartRequest(BaseModel):
    metadata: Metadata
    subject: Optional[Subject] = None
    settings: Optional[Settings] = None
    frame_a: Optional["ChartRequest"] = None


TransitType = Literal[
    "transit",
    "on_natal",
    "synastry",
    "astrocartography",
    "solar_arc",
    "secondary_progression",
    "secondary_progression_100y",
    "timeline_major",
    "eclipses",
    "eclipse_transits",
    "lunations",
]


class TransitMetadata(BaseModel):
    transit_type: TransitType
    timestamp_utc: Optional[str] = None
    location: Optional[LocationInput] = None
    solar_arc_sun: Optional[Literal["mean", "true"]] = None
    output: Optional[Literal["aspects", "chart"]] = None
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None
    lunation_type: Optional[str] = None
    eclipse_kind: Optional[str] = None


class TransitRequest(BaseModel):
    metadata: TransitMetadata
    frame_a: Optional[ChartRequest] = None
    frame_b: Optional[ChartRequest] = None


TimelineLevel = Literal[
    "level1",
    "level2",
    "level3",
    "outer",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "nodes",
    "lunations",
    "eclipses",
    "new_moon",
    "full_moon",
    "solar_eclipse",
    "lunar_eclipse",
]


class TimelineMetadata(BaseModel):
    start_utc: str
    end_utc: str
    level: TimelineLevel
    body: Optional[str] = None


class TimelineRequest(BaseModel):
    metadata: TimelineMetadata
    natal: ChartRequest
    settings: Optional[Settings] = None


class ProgressionTimelineMetadata(BaseModel):
    start_utc: str
    end_utc: str
    step_years: Optional[int] = 1
    output: Optional[Literal["aspects", "chart"]] = None


class ProgressionTimelineRequest(BaseModel):
    metadata: ProgressionTimelineMetadata
    natal: ChartRequest
    settings: Optional[Settings] = None


ChartRequest.model_rebuild()
