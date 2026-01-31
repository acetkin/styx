"""Application constants and defaults."""

DEFAULT_HOUSE_SYSTEM = "placidus"
DEFAULT_ZODIAC = "tropical"
DEFAULT_COORDINATE_SYSTEM = "ecliptic"
DEFAULT_STAR_ORB = 2.0

PLANET_ORDER = [
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
]

ASTEROID_ORDER = [
    "ceres",
    "pallas",
    "juno",
    "vesta",
    "chiron",
    "lilith (black moon)",
    "lilith (asteroid)",
]

DEFAULT_FIXED_STARS = [
    "Regulus",
    "Spica",
    "Aldebaran",
    "Antares",
    "Fomalhaut",
    "Sirius",
    "Betelgeuse",
    "Rigel",
    "Procyon",
    "Vega",
]

ASPECT_SET = "major_minor"
ASPECT_ANGLES = [0.0, 60.0, 90.0, 120.0, 180.0, 30.0, 45.0, 72.0, 135.0, 150.0]
ASPECT_ORBS = {
    0.0: 8.0,
    60.0: 6.0,
    90.0: 6.0,
    120.0: 6.0,
    180.0: 8.0,
    30.0: 6.0,
    45.0: 6.0,
    72.0: 6.0,
    135.0: 6.0,
    150.0: 6.0,
}
ASPECT_CLASSES = {
    0.0: "major",
    60.0: "major",
    90.0: "major",
    120.0: "major",
    180.0: "major",
    30.0: "minor",
    45.0: "minor",
    72.0: "minor",
    135.0: "minor",
    150.0: "minor",
}

TRANSIT_ORB_TABLE = {
    "jupiter": 3.0,
    "saturn": 3.0,
    "uranus": 4.0,
    "neptune": 4.0,
    "pluto": 4.0,
    "nodes": 2.0,
}

PROGRESSION_ORB_DEFAULT = 2.0

HOUSE_SYSTEM_MAP = {
    "placidus": "P",
}

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]
