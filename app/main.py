"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.memory.sqlite_store import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()

    app = FastAPI(
        title="Enterprise AI Research Agent",
        description=(
            "Transformation research API — multi-agent brief with sources, "
            "recommendations, and PDF export."
        ),
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
