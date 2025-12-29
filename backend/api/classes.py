"""
Class management API endpoints.
Full CRUD operations for managing teaching classes.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query

from ..models.database import db
from ..models.schemas import (
    ClassCreateRequest,
    ClassUpdateRequest,
    ClassInfo,
    ClassListResponse,
)

router = APIRouter(prefix="/classes", tags=["classes"])


@router.post("", response_model=ClassInfo)
async def create_class(request: ClassCreateRequest):
    """
    创建新班级
    """
    class_id = str(uuid4())
    timestamp = datetime.now().isoformat()

    await db.execute(
        """
        INSERT INTO classes (id, name, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (class_id, request.name, request.description, timestamp, timestamp),
        commit=True,
    )

    return ClassInfo(
        id=class_id,
        name=request.name,
        description=request.description,
        created_at=timestamp,
        updated_at=timestamp,
    )


@router.get("", response_model=ClassListResponse)
async def list_classes(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
):
    """
    获取班级列表（分页）
    """
    # Get total count
    count_row = await db.fetch_one("SELECT COUNT(*) as count FROM classes")
    total = count_row["count"] if count_row else 0

    # Get paginated classes
    offset = (page - 1) * limit
    rows = await db.fetch_all(
        "SELECT * FROM classes ORDER BY name LIMIT ? OFFSET ?",
        (limit, offset),
    )

    classes = [ClassInfo(**dict(row)) for row in rows]
    return ClassListResponse(classes=classes, total=total)


@router.get("/{class_id}", response_model=ClassInfo)
async def get_class(class_id: str):
    """
    获取指定班级详情
    """
    row = await db.fetch_one(
        "SELECT * FROM classes WHERE id = ?",
        (class_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="班级不存在")

    return ClassInfo(**dict(row))


@router.put("/{class_id}", response_model=ClassInfo)
async def update_class(class_id: str, request: ClassUpdateRequest):
    """
    更新班级信息
    """
    # Check if exists
    row = await db.fetch_one("SELECT id FROM classes WHERE id = ?", (class_id,))
    if not row:
        raise HTTPException(status_code=404, detail="班级不存在")

    # Build update query dynamically
    update_fields = []
    params = []

    if request.name is not None:
        update_fields.append("name = ?")
        params.append(request.name)
    if request.description is not None:
        update_fields.append("description = ?")
        params.append(request.description)

    if update_fields:
        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(class_id)

        await db.execute(
            f"UPDATE classes SET {', '.join(update_fields)} WHERE id = ?",
            tuple(params),
            commit=True,
        )

    # Return updated class
    row = await db.fetch_one("SELECT * FROM classes WHERE id = ?", (class_id,))
    return ClassInfo(**dict(row))


@router.delete("/{class_id}")
async def delete_class(class_id: str):
    """
    删除班级
    """
    # Check if exists
    row = await db.fetch_one("SELECT id FROM classes WHERE id = ?", (class_id,))
    if not row:
        raise HTTPException(status_code=404, detail="班级不存在")

    await db.execute("DELETE FROM classes WHERE id = ?", (class_id,), commit=True)
    return {"message": "班级删除成功"}
