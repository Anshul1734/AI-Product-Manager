"""
FastAPI application factory.

Everything the browser calls lives under `/api/v1`, so the deployment needs a
single routing rule and there is one code path in production -- the previous
setup had a duplicate self-contained serverless entrypoint that drifted from
this app, which is how the two copies ended up disagreeing about response
shapes.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config.settings import settings
from .core.logging.logger import app_logger
from .rag.retriever import get_store
from .routers import (
    export_router,
    health_router,
    knowledge_router,
    memory_router,
    workflow_router,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load the knowledge index during startup so the first request does not pay
    # for it. On serverless this runs once per cold start.
    store = get_store()

    app_logger.info(
        "Application starting",
        version=settings.APP_VERSION,
        llm_configured=settings.llm_configured,
        model=settings.GROQ_MODEL,
        corpus_chunks=store.size,
        dense_retrieval=store.has_dense,
        serverless=settings.is_serverless,
    )
    if not settings.llm_configured:
        app_logger.warning("GROQ_API_KEY is not set; /generate will return a configuration error")

    yield

    app_logger.info("Application shutting down")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Multi-agent product planning. A graph of specialist agents turns a product "
            "idea into a vision, PRD, RICE-scored roadmap, architecture and backlog, "
            "grounded in a retrieval corpus of product-management practice."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    origins = settings.get_cors_origins()
    wildcard = "*" in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # The CORS spec forbids credentials with a wildcard origin, and browsers
        # reject the combination outright rather than degrading.
        allow_credentials=not wildcard,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    prefix = settings.API_V1_STR
    app.include_router(health_router, prefix=prefix)
    app.include_router(workflow_router, prefix=prefix)
    app.include_router(knowledge_router, prefix=prefix)
    app.include_router(memory_router, prefix=prefix)
    app.include_router(export_router, prefix=prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> Dict[str, Any]:
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "ok",
            "api": prefix,
            "docs": "/docs",
        }

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        app_logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
            error=str(exc)[:500],
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "error_type": type(exc).__name__,
                # Detail only in debug: error strings can carry prompt content.
                "detail": str(exc)[:500] if settings.DEBUG else None,
            },
        )

    return app


app = create_application()
