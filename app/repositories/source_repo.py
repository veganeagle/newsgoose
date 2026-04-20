import json
from app.models import Source
from app.config import BASE_DIR


_SOURCES_FILE = BASE_DIR / "data" / "sources.json"


def _load_sources() -> list[Source]:
    data = json.loads(_SOURCES_FILE.read_text(encoding="utf-8"))
    return [Source(**item) for item in data]


_SOURCES: list[Source] = _load_sources()


def list_enabled_sources() -> list[Source]:
    return sorted(
        [s for s in _SOURCES if s.is_enabled],
        key=lambda s: s.sort_order,
    )


def get_source(source_key: str) -> Source | None:
    for source in _SOURCES:
        if source.source_key == source_key:
            return source
    return None