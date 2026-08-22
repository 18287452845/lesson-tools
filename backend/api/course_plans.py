"""
Standalone Course Plan API endpoints.

Builds editable Yunlin teaching/experiment plan drafts from already generated
lesson plans and exports them as fixed-template Word documents.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..models.schemas import (
    CoursePlanCreateRequest,
    CoursePlanDetail,
    CoursePlanListResponse,
    CoursePlanUpdateRequest,
)
from ..services.course_plan_service import (
    CoursePlanTemplateError,
    course_plan_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["course_plans"])


@router.post("/course-plans", response_model=CoursePlanDetail)
async def create_course_plan(request: CoursePlanCreateRequest):
    """Create a semester-plan draft from selected generated lesson plans."""
    try:
        return await course_plan_service.create_draft(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create course plan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/course-plans", response_model=CoursePlanListResponse)
async def list_course_plans(
    status: str = Query(None, description="Filter by status (draft, exported)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List standalone semester-plan drafts."""
    try:
        course_plans, total = await course_plan_service.list_course_plans(
            status=status, page=page, limit=limit
        )
        return CoursePlanListResponse(course_plans=course_plans, total=total)
    except Exception as e:
        logger.error(f"Failed to list course plans: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/course-plans/{course_plan_id}", response_model=CoursePlanDetail)
async def get_course_plan(course_plan_id: str):
    """Get the full editable state of a semester plan."""
    plan = await course_plan_service.get_course_plan(course_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"学期计划 {course_plan_id} 不存在")
    return plan


@router.put("/course-plans/{course_plan_id}", response_model=CoursePlanDetail)
async def update_course_plan(course_plan_id: str, request: CoursePlanUpdateRequest):
    """Save edited metadata and lesson rows of a semester plan."""
    try:
        return await course_plan_service.update_course_plan(course_plan_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update course plan {course_plan_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/course-plans/{course_plan_id}/export")
async def export_course_plan(course_plan_id: str):
    """Render the semester plan into fixed-template docx file(s) and download."""
    try:
        file_path, media_type = await course_plan_service.export_course_plan(
            course_plan_id
        )
    except CoursePlanTemplateError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to export course plan {course_plan_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(
        file_path,
        media_type=media_type,
        filename=Path(file_path).name,
    )


@router.delete("/course-plans/{course_plan_id}")
async def delete_course_plan(course_plan_id: str):
    """Delete a semester-plan draft."""
    try:
        await course_plan_service.delete_course_plan(course_plan_id)
        return {"message": f"学期计划 {course_plan_id} 已删除"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
