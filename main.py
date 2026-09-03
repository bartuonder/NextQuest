"""NextQuest application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import api_router
from core.config import settings
from core.database import init_db

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
)
logger = logging.getLogger("nextquest")

WEB_DIR = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    logger.info(
        "%s %s ready (env=%s, llm=%s)",
        settings.app_name,
        settings.app_version,
        settings.environment,
        "on" if settings.llm_enabled else "off",
    )
    if not settings.llm_enabled:
        logger.warning("OPENAI_API_KEY is missing; /api/recommendations will return 503.")
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    summary="Tell NextQuest three titles you love per category and get fresh picks back.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "llm_enabled": settings.llm_enabled,
    }


if WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
