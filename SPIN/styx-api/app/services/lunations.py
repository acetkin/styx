from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_LUNATIONS_CACHE: list["LunationEvent"] | None = None


@dataclass(frozen=True)
class LunationEvent:
    timestamp_utc: str
    type: str
    eclipse_kind: str

    @property
    def dt(self) -> datetime:
        raw = self.timestamp_utc
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


def _default_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "lunations_100y.csv"


def _parse_filters(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace("|", ",").split(",") if p.strip()]
    if not parts:
        return None
    if len(parts) == 1 and parts[0].lower() in {"all", "*"}:
        return None
    return {p for p in parts}


def load_lunations(path: Path | None = None) -> list[LunationEvent]:
    global _LUNATIONS_CACHE
    if _LUNATIONS_CACHE is not None:
        return _LUNATIONS_CACHE

    if path is None:
        path = _default_path()
    if not path.exists():
        raise RuntimeError(f"lunations_file_missing:{path}")

    events: list[LunationEvent] = []
    with path.open("r", encoding="utf-8") as handle:
        header = handle.readline()
        if not header:
            raise RuntimeError("lunations_file_empty")
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            parts = [p.strip() for p in raw.split(",")]
            if len(parts) < 2:
                continue
            timestamp = parts[0]
            evt_type = parts[1]
            eclipse_kind = parts[2] if len(parts) > 2 else ""
            events.append(LunationEvent(timestamp_utc=timestamp, type=evt_type, eclipse_kind=eclipse_kind))

    _LUNATIONS_CACHE = events
    return events


def filter_lunations(
    start_utc: str,
    end_utc: str,
    lunation_type: str | None = None,
    eclipse_kind: str | None = None,
    path: Path | None = None,
) -> list[dict]:
    start_event = LunationEvent(timestamp_utc=start_utc, type="start", eclipse_kind="")
    end_event = LunationEvent(timestamp_utc=end_utc, type="end", eclipse_kind="")

    type_filter = _parse_filters(lunation_type)
    kind_filter = _parse_filters(eclipse_kind)

    events = load_lunations(path)
    results: list[dict] = []
    for event in events:
        dt = event.dt
        if dt < start_event.dt or dt > end_event.dt:
            continue
        if type_filter and event.type not in type_filter:
            continue
        if kind_filter and event.eclipse_kind not in kind_filter:
            continue
        results.append(
            {
                "timestamp_utc": event.timestamp_utc,
                "type": event.type,
                "eclipse_kind": event.eclipse_kind,
            }
        )
    return results
