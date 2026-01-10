"""
FastAPI application entry point for the Lesson Plan Tool.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from .config import settings
from .models.database import init_db
from .api import templates, generate, edit, documents, settings as settings_api, batch, classes, lesson_plans
from .services.template_sync import sync_templates_on_startup

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Initialize database on startup
    await init_db()

    # Sync templates from storage/templates/ folder to database
    try:
        await sync_templates_on_startup()
    except Exception as e:
        logger.error(f"模板同步失败: {str(e)}")

    yield
    # Cleanup on shutdown


# Create FastAPI application
app = FastAPI(
    title="Lesson Plan Tool API",
    description="智能教案生成与编辑工具 API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "https://ls.linnera.link",
        "http://ls.linnera.link",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for file downloads
app.mount("/static", StaticFiles(directory=str(settings.output_dir)), name="static")

# Include routers
app.include_router(templates.router, prefix=settings.api_prefix, tags=["templates"])
app.include_router(generate.router, prefix=settings.api_prefix, tags=["generate"])
app.include_router(edit.router, prefix=settings.api_prefix, tags=["edit"])
app.include_router(documents.router, prefix=settings.api_prefix, tags=["documents"])
app.include_router(settings_api.router, prefix=settings.api_prefix, tags=["settings"])
app.include_router(batch.router, prefix=settings.api_prefix, tags=["batch"])
app.include_router(classes.router, prefix=settings.api_prefix, tags=["classes"])
app.include_router(lesson_plans.router, prefix=settings.api_prefix, tags=["lesson_plans"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Lesson Plan Tool API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
