from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import TILE_REFRESH_SECONDS
from app.repositories.article_repo import get_articles_for_source
from app.repositories.source_repo import get_source

router = APIRouter()

LOCAL_TZ = ZoneInfo("America/Toronto")


def register_templates(templates_obj: Jinja2Templates) -> None:
    global templates
    templates = templates_obj


def _to_local(dt):
    return dt.astimezone(LOCAL_TZ)

@router.get("/tile/{source_key}")
async def tile(request: Request, source_key: str, slot_index: int | None = None):
    source = get_source(source_key)
    print(f"route: /tile/{source_key} slot={slot_index}")
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    articles = get_articles_for_source(source_key)

    return templates.TemplateResponse(
        request=request,
        name="partials/tile.html",
        context={
            "source": source,
            "slot_index": slot_index,
            "articles": articles,
            "refresh_seconds": TILE_REFRESH_SECONDS,
            "to_local": _to_local,
        },
    )