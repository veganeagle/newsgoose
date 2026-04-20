from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    source_key: str
    title: str
    url: str
    published_at: datetime
    summary: Optional[str]
    image_url: Optional[str]
    guid: str
    pulled_at: datetime


@dataclass
class Source:
    source_key: str
    display_name: str
    feed_url: str
    tile_type: str = "news"
    icon_url: Optional[str] = None
    is_enabled: bool = True
    sort_order: int = 0