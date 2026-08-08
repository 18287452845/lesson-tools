"""
FastAPI application entry point for the Lesson Plan Tool.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from .config import settings
from .models.database import init_db, db
from .api import templates, generate, edit, documents, settings as settings_api, batch, classes, lesson_plans, textbooks, textbook_discovery, subjects, grades, competition, preparation
from .services.builtin_template import (
    ensure_builtin_template_registered,
    validate_all_builtin_templates,
)
from .services.metadata_sync import init_metadata

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Initialize database on startup
    await init_db()

    # Initialize preset subjects and grades
    try:
        await init_metadata(db)
    except Exception as e:
        logger.error(f"元数据初始化失败: {str(e)}")

    # Validate and register the immutable Yunlin template resource.
    try:
        await ensure_builtin_template_registered()
        invalid_templates = [
            report for report in validate_all_builtin_templates() if not report["is_valid"]
        ]
        if invalid_templates:
            raise ValueError(
                "；".join(
                    f"{report['name']}：{'、'.join(report['errors'])}"
                    for report in invalid_templates
                )
            )
    except Exception as e:
        logger.error(f"模板同步失败: {str(e)}")

    yield
    # Cleanup on shutdown


# Create FastAPI application
app = FastAPI(
    title="Yunlin Teaching Preparation API",
    description="智能教案生成与编辑工具 API",
    version="1.1.0",
    lifespan=lifespan,
)

# Configure CORS
cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
    "http://localhost:5178",
    "https://ls.linnera.link",
    "http://ls.linnera.link",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
app.include_router(textbooks.router, prefix=settings.api_prefix, tags=["textbooks"])
app.include_router(textbook_discovery.router, prefix=settings.api_prefix, tags=["textbook-discovery"])
app.include_router(subjects.router, prefix=settings.api_prefix, tags=["subjects"])
app.include_router(grades.router, prefix=settings.api_prefix, tags=["grades"])
app.include_router(competition.router, prefix=settings.api_prefix, tags=["competition"])
app.include_router(preparation.router, prefix=settings.api_prefix, tags=["preparation"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Yunlin Teaching Preparation API",
        "version": "1.1.0",
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
