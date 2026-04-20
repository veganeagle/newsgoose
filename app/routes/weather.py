from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.services.weather_service import fetch_weather, reverse_geocode_label
from app.repositories.weather_repo import get_weather

router = APIRouter()

LOCAL_TZ = ZoneInfo("America/Toronto")


def register_templates(templates_obj: Jinja2Templates) -> None:
    global templates
    templates = templates_obj


def _to_local(dt):
    return dt.astimezone(LOCAL_TZ)


@router.get("/weather")
async def weather_bar(request: Request, lat: float | None = None, lon: float | None = None):
    if lat is not None and lon is not None:
        label = await reverse_geocode_label(lat, lon)
        weather = await fetch_weather(lat, lon, label)
    else: weather = get_weather()

    return templates.TemplateResponse(
        request=request,
        name="partials/weather.html",
        context={
            "weather": weather,
            "to_local": _to_local,
        },
    )