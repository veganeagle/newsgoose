from __future__ import annotations

import asyncio
from pathlib import Path

import feedparser
import httpx


async def fetch_feed(source_key: str, feed_url: str):
    print(f"fetch_feed[{source_key}]: GET {feed_url}")

    timeout = httpx.Timeout(15.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(
            feed_url,
            headers={"User-Agent": "newsviewer/0.1"},
        )

    content_type = resp.headers.get("content-type", "")
    print(
        f"fetch_feed[{source_key}]: status={resp.status_code} "
        f"bytes={len(resp.text)} content_type={content_type}"
    )

    Path(f"debug_{source_key}_feed.xml").write_text(resp.text, encoding="utf-8")

    if "<html" in resp.text[:500].lower():
        print(f"fetch_feed[{source_key}]: response looks like HTML, not RSS")

    parsed = await asyncio.to_thread(feedparser.parse, resp.text)

    print(f"fetch_feed[{source_key}]: entries={len(parsed.entries)}")

    return parsed