from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app.config import BASE_DIR
from app.repositories.article_repo import Article


_TOPIC_THUMBS_FILE = BASE_DIR / "data" / "topic_thumbs.json"


def _load_topic_thumb_rules() -> list[dict]:
    return json.loads(_TOPIC_THUMBS_FILE.read_text(encoding="utf-8"))


_TOPIC_THUMB_RULES = _load_topic_thumb_rules()


def _first(entry, *keys):
    for key in keys:
        value = entry.get(key)
        if value:
            return value
    return None


def _get_title(entry) -> str:
    return (_first(entry, "title", "headline") or "").strip()


def _get_url(entry) -> str | None:
    return _first(entry, "link", "url", "id", "guid")


def _get_guid(entry, url: str | None) -> str | None:
    return _first(entry, "id", "guid") or url


def _get_summary(entry) -> str | None:
    return _first(entry, "summary", "description")


def _get_category_terms(entry) -> list[str]:
    tags = entry.get("tags") or []
    out: list[str] = []

    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict):
                term = tag.get("term")
                if term:
                    out.append(term.strip().lower())
            elif isinstance(tag, str):
                out.append(tag.strip().lower())

    category = entry.get("category")
    if isinstance(category, str) and category.strip():
        out.append(category.strip().lower())

    return out


def _get_topic_thumbnail(entry) -> str | None:
    title = _get_title(entry).lower()
    categories = _get_category_terms(entry)

    best_url = None
    best_priority = -1

    for rule in _TOPIC_THUMB_RULES:
        match_type = (rule.get("match_type") or "").strip().lower()
        pattern = (rule.get("pattern") or "").strip().lower()
        thumbnail_url = rule.get("thumbnail_url")
        priority = int(rule.get("priority") or 0)

        if not pattern or not thumbnail_url:
            continue

        matched = False

        if match_type == "title":
            matched = pattern in title
        elif match_type == "category":
            matched = any(pattern in category for category in categories)

        if matched and priority > best_priority:
            best_priority = priority
            best_url = thumbnail_url

    return best_url


def _coerce_datetime(entry, pulled_at: datetime) -> datetime:
    raw_value = _first(entry, "published", "updated", "pubDate")
    if raw_value:
        try:
            dt = parsedate_to_datetime(raw_value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        try:
            return datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    return pulled_at


def _extract_image_url(entry) -> str | None:
    custom_image = entry.get("imageurl")
    if custom_image:
        return custom_image

    media_content = entry.get("media_content")
    if media_content and isinstance(media_content, list):
        first = media_content[0]
        if isinstance(first, dict):
            url = first.get("url")
            if url:
                return url

    media_thumbnail = entry.get("media_thumbnail")
    if media_thumbnail and isinstance(media_thumbnail, list):
        first = media_thumbnail[0]
        if isinstance(first, dict):
            url = first.get("url")
            if url:
                return url

    enclosures = entry.get("enclosures")
    if enclosures and isinstance(enclosures, list):
        first = enclosures[0]
        if isinstance(first, dict):
            href = first.get("href") or first.get("url")
            if href:
                return href

    links = entry.get("links")
    if links and isinstance(links, list):
        for link in links:
            if isinstance(link, dict) and link.get("type", "").startswith("image/"):
                return link.get("href")

    summary = _get_summary(entry) or ""
    match = re.search(r"""<img[^>]+src=['"]([^'"]+)['"]""", summary, re.IGNORECASE)
    if match:
        return match.group(1)

    return _get_topic_thumbnail(entry)


def normalize_entries(source_key: str, parsed_feed, pulled_at: datetime) -> list[Article]:
    seen: set[str] = set()
    articles: list[Article] = []

    for entry in parsed_feed.entries:
        url = _get_url(entry)
        guid = _get_guid(entry, url)

        if not url:
            continue

        dedupe_key = guid or url
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        title = _get_title(entry)
        if not title:
            continue

        articles.append(
            Article(
                source_key=source_key,
                title=title,
                url=url,
                published_at=_coerce_datetime(entry, pulled_at),
                summary=_get_summary(entry),
                image_url=_extract_image_url(entry),
                guid=guid or url,
                pulled_at=pulled_at,
            )
        )

    articles.sort(key=lambda a: a.published_at, reverse=True)
    return articles