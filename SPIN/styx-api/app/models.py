from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocationObj(RequestModel):
    lat: float
    lon: float
    alt_m: float = 0
    place: Optional[str] = None


LocationInput = Union[str, LocationObj]


ChartType = Literal["natal", "moment", "solar_arc", "secondary_progression"]


class Metadata(RequestModel):
    chart_type: ChartType
    timestamp_utc: Optional[str] = None
    location: Optional[LocationInput] = None
    solar_arc_sun: Optional[Literal["mean", "true"]] = None


class PointsSettings(RequestModel):
    lilith: Optional[Literal["mean", "true"]] = None


class Settings(RequestModel):
    house_system: str = Field(default="placidus")
    zodiac: str = Field(default="tropical")
    coordinate_system: str = Field(default="ecliptic")
    points: Optional[PointsSettings] = None


class ChartRequest(RequestModel):
    metadata: Metadata
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


class TransitMetadata(RequestModel):
    transit_type: TransitType
    timestamp_utc: Optional[str] = None
    location: Optional[LocationInput] = None
    solar_arc_sun: Optional[Literal["mean", "true"]] = None
    start_utc: Optional[str] = None
    end_utc: Optional[str] = None
    lunation_type: Optional[str] = None
    eclipse_kind: Optional[str] = None


class TransitRequest(RequestModel):
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


class TimelineMetadata(RequestModel):
    start_utc: str
    end_utc: str
    level: TimelineLevel
    body: Optional[str] = None


class TimelineRequest(RequestModel):
    metadata: TimelineMetadata
    natal: ChartRequest
    settings: Optional[Settings] = None


class ProgressionTimelineMetadata(RequestModel):
    start_utc: str
    end_utc: str
    step_years: Optional[int] = 1
    output: Optional[Literal["aspects", "chart"]] = None


class ProgressionTimelineRequest(RequestModel):
    metadata: ProgressionTimelineMetadata
    natal: ChartRequest
    settings: Optional[Settings] = None


ChartRequest.model_rebuild()
