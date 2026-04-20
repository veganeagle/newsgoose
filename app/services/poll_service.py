from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.config import (
    MAX_ITEMS_PER_SOURCE,
    POLL_INTERVAL_SECONDS,
    WEATHER_LABEL,
    WEATHER_LATITUDE,
    WEATHER_LONGITUDE,
    WEATHER_REFRESH_SECONDS,
)
from app.repositories.article_repo import replace_articles_for_source
from app.repositories.source_repo import list_enabled_sources
from app.repositories.weather_repo import get_weather, set_weather
from app.services.feed_service import fetch_feed
from app.services.normalize_service import normalize_entries
from app.services.weather_service import fetch_weather

logger = logging.getLogger(__name__)


async def poll_once() -> None:
    sources = list_enabled_sources()
    logger.info("poll_once: sources=%s", len(sources))

    for source in sources:
        logger.info("poll_once: fetching %s", source.source_key)
        try:
            pulled_at = datetime.now(timezone.utc)
            parsed_feed = await fetch_feed(source.source_key, source.feed_url)

            logger.info("poll_once: parsed %s", source.source_key)

            articles = normalize_entries(source.source_key, parsed_feed, pulled_at)

            logger.info("poll_once: normalized %s count=%s", source.source_key, len(articles))

            replace_articles_for_source(
                source_key=source.source_key,
                articles=articles,
                max_items=MAX_ITEMS_PER_SOURCE,
            )

        except Exception:
            logger.exception("poll failed for source=%s", source.source_key)

    try:
        current = get_weather()
        now = datetime.now(timezone.utc)

        should_refresh = (
            current is None
            or (now - current.fetched_at) >= timedelta(seconds=WEATHER_REFRESH_SECONDS)
        )

        if should_refresh:
            logger.info("poll_once: refreshing weather")
            snapshot = await fetch_weather(
                lat=WEATHER_LATITUDE,
                lon=WEATHER_LONGITUDE,
                label=WEATHER_LABEL,
            )
            set_weather(snapshot)
    except Exception:
        logger.exception("weather refresh failed")


async def poll_loop() -> None:
    while True:
        try:
            await poll_once()
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("poll_loop: cancelled")
            raise
        except Exception:
            logger.exception("poll loop iteration failed")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)