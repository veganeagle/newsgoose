from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


WEATHER_CODE_LABELS = {
    0: "Clear",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Cloudy",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Heavy showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm + hail",
    99: "Severe thunderstorm",
}
_reverse_geocode_cache: dict[tuple[float, float], str] = {}

@dataclass
class WeatherSnapshot:
    label: str
    temperature_c: float | None
    apparent_temperature_c: float | None
    condition: str
    precipitation_probability: int | None
    precipitation_mm: float | None
    rest_of_day: str
    fetched_at: datetime


def _code_label(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WEATHER_CODE_LABELS.get(code, "Unknown")


def _build_rest_of_day(hourly: dict[str, Any], now_utc: datetime) -> str:
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    probs = hourly.get("precipitation_probability") or []
    precips = hourly.get("precipitation") or []
    codes = hourly.get("weather_code") or []

    upcoming: list[int] = []
    for i, raw in enumerate(times):
        try:
            dt = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt >= now_utc:
            upcoming.append(i)

    upcoming = upcoming[:8]
    if not upcoming:
        return "No later-day forecast available."

    max_temp = None
    max_pop = 0
    total_precip = 0.0
    seen_codes: list[int] = []

    for i in upcoming:
        if i < len(temps) and temps[i] is not None:
            max_temp = temps[i] if max_temp is None else max(max_temp, temps[i])

        if i < len(probs) and probs[i] is not None:
            max_pop = max(max_pop, int(probs[i]))

        if i < len(precips) and precips[i] is not None:
            total_precip += float(precips[i])

        if i < len(codes) and codes[i] is not None:
            seen_codes.append(int(codes[i]))

    condition = _code_label(seen_codes[0] if seen_codes else None)

    parts = [condition]
    if max_temp is not None:
        parts.append(f"high near {round(max_temp)}°C")
    if max_pop:
        parts.append(f"{max_pop}% precip")
    if total_precip > 0:
        parts.append(f"{total_precip:.1f} mm expected")

    return " • ".join(parts)

def _reverse_geocode_cache_key(lat: float, lon: float) -> tuple[float, float]:
    return (round(lat, 3), round(lon, 3))

async def reverse_geocode_label(lat: float, lon: float) -> str:
    cache_key = _reverse_geocode_cache_key(lat, lon)
    cached = _reverse_geocode_cache.get(cache_key)
    if cached:
        return cached

    params = {"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1}
    headers = {"User-Agent": "news-dashboard/1.0"}
    timeout = httpx.Timeout(15.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = await client.get("https://nominatim.openstreetmap.org/reverse", params=params)
        resp.raise_for_status()
        data = resp.json()

    address = data.get("address") or {}
    city = (address.get("city") or address.get("town") or address.get("village") or address.get("municipality") or address.get("county"))
    state = address.get("state")
    if city and state:
        label = f"{city}, {state}"
    elif city:
        label = city
    else:
        label = "Your location"
    _reverse_geocode_cache[cache_key] = label
    return label

async def fetch_weather(lat: float, lon: float, label: str) -> WeatherSnapshot:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,weather_code",
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
        "timezone": "GMT",
        "forecast_days": 1,
    }

    timeout = httpx.Timeout(15.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        resp.raise_for_status()
        data = resp.json()

    now_utc = datetime.now(timezone.utc)
    current = data.get("current") or {}
    hourly = data.get("hourly") or {}

    current_code = current.get("weather_code")

    current_pop = None
    current_precip = None
    hourly_times = hourly.get("time") or []
    try:
        current_time = current.get("time")
        if current_time in hourly_times:
            idx = hourly_times.index(current_time)
            hourly_probs = hourly.get("precipitation_probability") or []
            hourly_precips = hourly.get("precipitation") or []

            if idx < len(hourly_probs):
                current_pop = hourly_probs[idx]
            if idx < len(hourly_precips):
                current_precip = hourly_precips[idx]
    except Exception:
        pass

    return WeatherSnapshot(
        label=label,
        temperature_c=current.get("temperature_2m"),
        apparent_temperature_c=current.get("apparent_temperature"),
        condition=_code_label(current_code),
        precipitation_probability=current_pop,
        precipitation_mm=current_precip,
        rest_of_day=_build_rest_of_day(hourly, now_utc),
        fetched_at=now_utc,
    )