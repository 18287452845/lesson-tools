"""
Lesson Plan Management API endpoints.

Provides CRUD operations for lesson plans, including:
- List lesson plans with filtering
- Get individual lesson plan details
- Update lesson plan fields
- Regenerate fields using AI
- Publish draft lesson plans to generate documents
- Batch operations (publish, delete)
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..config import settings
from ..models.database import get_db
from ..models.schemas import (
    LessonPlan,
    LessonPlanListResponse,
    UpdateFieldRequest,
    RegenerateFieldRequest,
    RegenerateFieldResponse,
    PublishResponse,
    BatchPublishRequest,
    BatchDeleteRequest,
)
from ..services.lesson_plan_service import LessonPlanService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["lesson_plans"])

# Initialize lesson plan service
lesson_plan_service = LessonPlanService()


@router.get("/lesson-plans", response_model=LessonPlanListResponse)
async def list_lesson_plans(
    status: Optional[str] = Query(None, description="Filter by status"),
    template_id: Optional[str] = Query(None, description="Filter by template"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    grade: Optional[str] = Query(None, description="Filter by grade"),
    search: Optional[str] = Query(None, description="Search in title and topic"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    List lesson plans with optional filtering and pagination.

    Supports filtering by:
    - status: lesson plan status (draft, draft_cached, generated, published)
    - template_id: template ID
    - subject: subject name
    - grade: grade level
    - search: keyword search in title and topic
    """
    try:
        filters = {}
        if status:
            filters["status"] = status
        if template_id:
            filters["template_id"] = template_id
        if subject:
            filters["subject"] = subject
        if grade:
            filters["grade"] = grade
        if search:
            filters["search"] = search

        lesson_plans, total = await lesson_plan_service.list_lesson_plans(
            filters=filters,
            page=page,
            limit=limit
        )

        return LessonPlanListResponse(
            lesson_plans=lesson_plans,
            total=total
        )

    except Exception as e:
        logger.error(f"Failed to list lesson plans: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lesson-plans/{lesson_plan_id}", response_model=LessonPlan)
async def get_lesson_plan(lesson_plan_id: str):
    """
    Get a single lesson plan by ID.
    """
    try:
        lesson_plan = await lesson_plan_service.get_lesson_plan(lesson_plan_id)

        if not lesson_plan:
            raise HTTPException(status_code=404, detail="Lesson plan not found")

        return lesson_plan

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lesson plan {lesson_plan_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/lesson-plans/{lesson_plan_id}/field", response_model=LessonPlan)
async def update_field(
    lesson_plan_id: str,
    request: UpdateFieldRequest
):
    """
    Update a single field in a lesson plan.

    The field_value can be any valid JSON type (string, object, array, etc.)
    depending on the field being updated.
    """
    try:
        updated_plan = await lesson_plan_service.update_field(
            lesson_plan_id=lesson_plan_id,
            field_name=request.field_name,
            field_value=request.field_value
        )

        return updated_plan

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update field {request.field_name} for lesson plan {lesson_plan_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lesson-plans/{lesson_plan_id}/regenerate-field", response_model=RegenerateFieldResponse)
async def regenerate_field(
    lesson_plan_id: str,
    request: RegenerateFieldRequest
):
    """
    Regenerate a single field using AI.

    This will call the AI generator to create new content for the specified field,
    optionally using additional instructions.
    """
    try:
        field_value = await lesson_plan_service.regenerate_field(
            lesson_plan_id=lesson_plan_id,
            field_name=request.field_name,
            additional_instruction=request.additional_instruction
        )

        return RegenerateFieldResponse(
            field_name=request.field_name,
            field_value=field_value
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to regenerate field {request.field_name} for lesson plan {lesson_plan_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lesson-plans/{lesson_plan_id}/publish", response_model=PublishResponse)
async def publish_lesson_plan(lesson_plan_id: str):
    """
    Publish a draft lesson plan by generating a Word document.

    This converts a draft_cached lesson plan to published status and creates
    a .docx file using the template renderer.
    """
    try:
        output_path, download_url = await lesson_plan_service.publish_lesson_plan(lesson_plan_id)

        return PublishResponse(
            lesson_plan_id=lesson_plan_id,
            output_file_path=output_path,
            download_url=download_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish lesson plan {lesson_plan_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lesson-plans/batch-publish")
async def batch_publish(request: BatchPublishRequest):
    """
    Batch publish multiple lesson plans and return a ZIP file.

    If group_by_document is True, lesson plans will be grouped 2 per document.
    Otherwise, each lesson plan gets its own document.
    """
    try:
        zip_path = await lesson_plan_service.batch_publish(
            lesson_plan_ids=request.lesson_plan_ids,
            group_by_document=request.group_by_document
        )

        if not Path(zip_path).exists():
            raise HTTPException(status_code=404, detail="ZIP file not found")

        filename = Path(zip_path).name

        logger.info(f"Serving batch publish ZIP: {filename}")

        return FileResponse(
            path=str(zip_path),
            filename=filename,
            media_type="application/zip",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch publish lesson plans: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/lesson-plans/{lesson_plan_id}")
async def delete_lesson_plan(lesson_plan_id: str):
    """
    Delete a lesson plan by ID.
    """
    try:
        await lesson_plan_service.delete_lesson_plan(lesson_plan_id)

        return {"message": "Lesson plan deleted", "id": lesson_plan_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete lesson plan {lesson_plan_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lesson-plans/batch-delete")
async def batch_delete(request: BatchDeleteRequest):
    """
    Batch delete multiple lesson plans.
    """
    try:
        deleted_count = 0
        failed_ids = []

        for lesson_plan_id in request.lesson_plan_ids:
            try:
                await lesson_plan_service.delete_lesson_plan(lesson_plan_id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete lesson plan {lesson_plan_id}: {str(e)}")
                failed_ids.append(lesson_plan_id)

        return {
            "message": f"Deleted {deleted_count} lesson plans",
            "deleted_count": deleted_count,
            "failed_ids": failed_ids
        }

    except Exception as e:
        logger.error(f"Failed to batch delete lesson plans: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
