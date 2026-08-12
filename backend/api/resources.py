"""Teaching resource library API."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response

from ..models.schemas import (
    TeachingResource,
    TeachingResourceCreate,
    TeachingResourceListResponse,
    TeachingResourceUpdate,
)
from ..services import teaching_resource_service as service


router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("", response_model=TeachingResource, status_code=201)
async def create_resource(request: TeachingResourceCreate):
    return await service.create_resource(request.model_dump())


@router.get("", response_model=TeachingResourceListResponse)
async def list_resources(
    search: Optional[str] = None,
    resource_type: Optional[str] = None,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
    status: str = Query("active", pattern="^(active|archived)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    resources, total = await service.list_resources(
        search=search, resource_type=resource_type, subject=subject, grade=grade,
        status=status, page=page, limit=limit,
    )
    return TeachingResourceListResponse(resources=resources, total=total)


@router.get("/{resource_id}", response_model=TeachingResource)
async def get_resource(resource_id: str):
    resource = await service.get_resource(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="教学资源不存在")
    return resource


@router.patch("/{resource_id}", response_model=TeachingResource)
async def update_resource(resource_id: str, request: TeachingResourceUpdate):
    resource = await service.update_resource(
        resource_id, request.model_dump(exclude_unset=True)
    )
    if not resource:
        raise HTTPException(status_code=404, detail="教学资源不存在")
    return resource


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(resource_id: str):
    if not await service.delete_resource(resource_id):
        raise HTTPException(status_code=404, detail="教学资源不存在")
    return Response(status_code=204)
