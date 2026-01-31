# STYX API

Deterministic astrology computation API built on Swiss Ephemeris.

## Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
uvicorn app.main:app --reload
```

## Environment

- `SE_EPHE_PATH` : Path to Swiss Ephemeris files.
- `STYX_GEOCODE_STUB` : Optional geocode stub. Examples:
  - `1` (uses 0,0,0,"STUB")
  - `41.2795516,31.4229672,0,Karadeniz Eregli`
  - `{"lat":41.2795516,"lon":31.4229672,"alt_m":0,"place":"Karadeniz Eregli"}`

## Endpoints

- `GET /v1/health`
- `GET /v1/config`
- `POST /v1/chart`
