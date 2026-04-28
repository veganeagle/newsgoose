from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.repositories.source_repo import list_enabled_sources

router = APIRouter()


def register_templates(templates_obj: Jinja2Templates) -> None:
    global templates
    templates = templates_obj

@router.get("/dashboard")
async def dashboard(request: Request):
    print("route: /dashboard")
    sources = sorted(list_enabled_sources(), key=lambda s: s.sort_order)
    sources_json = [
        {
            "source_key": s.source_key,
            "display_name": s.display_name,
            "icon_url": s.icon_url,
            "categories": s.categories or [],
        }
        for s in sources
    ]

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
context={
    "sources": sources,
    "sources_json": sources_json},
    )