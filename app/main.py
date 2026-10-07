import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse, PlainTextResponse, Response

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_TITLE, STATIC_DIR, TEMPLATES_DIR
from app.routes import dashboard, tiles, weather
from app.services.poll_service import poll_loop

logging.basicConfig(level=logging.INFO, force=True)

_poll_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poll_task

    logging.info("startup: launching poll loop")
    _poll_task = asyncio.create_task(poll_loop())

    try:
        yield
    finally:
        logging.info("shutdown: stopping poll loop")
        if _poll_task:
            _poll_task.cancel()
            try:
                await _poll_task
            except asyncio.CancelledError:
                logging.info("shutdown: poll loop cancelled")


app = FastAPI(title=APP_TITLE, lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["now"] = lambda: datetime.now(timezone.utc)

dashboard.register_templates(templates)
tiles.register_templates(templates)
weather.register_templates(templates)


app.include_router(dashboard.router)
app.include_router(tiles.router)
app.include_router(weather.router)


@app.get("/")
async def root():
  # Permanent, so search engines treat /dashboard as the one home page.
  return RedirectResponse(url="/dashboard", status_code=301)


SITE_URL = "https://newsgoose.ca"


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return PlainTextResponse(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    urls = "".join(f"  <url><loc>{SITE_URL}{path}</loc></url>\n" for path in ("/dashboard", "/privacy"))
    body = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'
    return Response(body, media_type="application/xml")


@app.get("/sw.js")
async def service_worker():
    return FileResponse(
        str(STATIC_DIR / "sw.js"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )



@app.get("/.well-known/assetlinks.json", include_in_schema=False)
def assetlinks():
    return FileResponse(
        "app/static/.well-known/assetlinks.json",
        media_type="application/json",
    )


@app.get("/privacy")
async def privacy():
    return HTMLResponse("""
    <html><body>
    <h2>Privacy Policy</h2>
    <p>NewsGoose does not collect or store personal data.</p>
    <p>Location may be used temporarily to display local weather and is not stored.</p>
    </body></html>
    """)