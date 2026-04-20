import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
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

dashboard.register_templates(templates)
tiles.register_templates(templates)
weather.register_templates(templates)


app.include_router(dashboard.router)
app.include_router(tiles.router)
app.include_router(weather.router)


@app.get("/")
async def root():
    return {"ok": True, "dashboard": "/dashboard"}