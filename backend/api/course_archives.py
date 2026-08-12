"""Course and semester archive API."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ..models.schemas import (
    CourseArchive,
    CourseArchiveCreate,
    CourseArchiveListResponse,
    CourseArchiveUpdate,
)
from ..services import course_archive_service as service


router = APIRouter(prefix="/course-archives", tags=["course-archives"])


class CloneArchiveRequest(BaseModel):
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{4}$")
    semester: int = Field(..., ge=1, le=2)


@router.post("", response_model=CourseArchive, status_code=201)
async def create_archive(request: CourseArchiveCreate):
    return await service.create_archive(request.model_dump())


@router.get("", response_model=CourseArchiveListResponse)
async def list_archives(
    search: Optional[str] = None,
    academic_year: Optional[str] = None,
    semester: Optional[int] = Query(None, ge=1, le=2),
    status: str = Query("active", pattern="^(active|archived)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    archives, total = await service.list_archives(
        search=search, academic_year=academic_year, semester=semester,
        status=status, page=page, limit=limit,
    )
    return CourseArchiveListResponse(archives=archives, total=total)


@router.get("/{archive_id}", response_model=CourseArchive)
async def get_archive(archive_id: str):
    archive = await service.get_archive(archive_id)
    if not archive:
        raise HTTPException(status_code=404, detail="课程档案不存在")
    return archive


@router.patch("/{archive_id}", response_model=CourseArchive)
async def update_archive(archive_id: str, request: CourseArchiveUpdate):
    archive = await service.update_archive(
        archive_id, request.model_dump(exclude_unset=True)
    )
    if not archive:
        raise HTTPException(status_code=404, detail="课程档案不存在")
    return archive


@router.post("/{archive_id}/clone", response_model=CourseArchive, status_code=201)
async def clone_archive(archive_id: str, request: CloneArchiveRequest):
    archive = await service.clone_archive(
        archive_id, request.academic_year, request.semester
    )
    if not archive:
        raise HTTPException(status_code=404, detail="课程档案不存在")
    return archive


@router.delete("/{archive_id}", status_code=204)
async def delete_archive(archive_id: str):
    if not await service.archive_course(archive_id):
        raise HTTPException(status_code=404, detail="课程档案不存在")
    return Response(status_code=204)
