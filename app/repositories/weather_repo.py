from __future__ import annotations

from app.services.weather_service import WeatherSnapshot

_weather: WeatherSnapshot | None = None


def get_weather() -> WeatherSnapshot | None:
    return _weather


def set_weather(snapshot: WeatherSnapshot) -> None:
    global _weather
    _weather = snapshot