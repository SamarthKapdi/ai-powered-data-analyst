"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, datasets, insights, upload
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle hook."""
    # Startup
    app.state.datasets = {}  # in-memory store: {id: {"df": ..., "filename": ..., "info": ...}}
    logger.info("Application started.  Config: %s", settings)
    logger.info(
        "Gemini LLM: %s",
        "enabled" if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here" else "disabled (no API key)",
    )
    yield
    # Shutdown
    app.state.datasets.clear()
    logger.info("Application shut down – all in-memory datasets cleared.")


# ------------------------------------------------------------------
# App instance
# ------------------------------------------------------------------
app = FastAPI(
    title="AI Data Analyst API",
    description="Backend for the AI-powered Data Analyst application",
    version="1.0.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------
# CORS – allow the Vite dev server
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(analyze.router, prefix="/api/analyze", tags=["Analyze"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["Datasets"])
app.include_router(insights.router, prefix="/api/insights", tags=["Insights"])


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.get("/api/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": "1.0.0"}
