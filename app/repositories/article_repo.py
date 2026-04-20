from collections import defaultdict
from app.models import Article


_articles_by_source: dict[str, list[Article]] = defaultdict(list)


def replace_articles_for_source(
    source_key: str,
    articles: list[Article],
    max_items: int,
) -> None:
    _articles_by_source[source_key] = articles[:max_items]


def get_articles_for_source(source_key: str) -> list[Article]:
    return _articles_by_source.get(source_key, [])