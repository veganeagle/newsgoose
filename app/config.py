from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

APP_TITLE = "News + Markets Dashboard"

POLL_INTERVAL_SECONDS = 300
TILE_REFRESH_SECONDS = 300

MAX_ITEMS_PER_SOURCE = 50

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


# weather
import os

WEATHER_LATITUDE = float(os.getenv("WEATHER_LAT", "43.7696"))
WEATHER_LONGITUDE = float(os.getenv("WEATHER_LON", "-79.1873"))
WEATHER_LABEL = os.getenv("WEATHER_LABEL", "Scarborough, ON")


WEATHER_REFRESH_SECONDS = 1800  # 30 minutes