from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database.db import init_db
from backend.routers import enrich, results
from backend.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("database initialized")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Prospect Research Agent",
        version="1.0.0",
        description="AI-powered B2B prospect enrichment from a single URL.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(enrich.router)
    app.include_router(results.router)

    @app.get("/", tags=["health"])
    def root():
        return {"status": "ok", "service": "prospect-research-agent", "model": settings.GROQ_MODEL}

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
