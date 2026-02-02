from importlib.metadata import PackageNotFoundError, version

SCHEMA_VERSION = "1.0"
ENGINE_VERSION = "0.1.0"
EPHEMERIS_PROVIDER = "swisseph"


def _resolve_api_version() -> str:
    try:
        return version("styx-api")
    except PackageNotFoundError:
        return ENGINE_VERSION
    except Exception:
        return ENGINE_VERSION


API_VERSION = _resolve_api_version()
