"""
Subject management API endpoints.
Full CRUD operations for managing subjects with usage statistics and preset protection.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query

from ..models.database import db
from ..models.schemas import (
    SubjectCreateRequest,
    SubjectUpdateRequest,
    SubjectInfo,
    SubjectListResponse,
    SubjectWithUsageStats,
)

router = APIRouter(prefix="/subjects", tags=["subjects"])


async def get_subject_usage_stats(subject_name: str) -> dict:
    """Calculate usage statistics for a subject."""
    # Count templates
    template_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM templates WHERE subject = ?",
        (subject_name,),
    )
    template_count = template_row["count"] if template_row else 0

    # Count lesson plans
    lesson_plan_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM lesson_plans WHERE subject = ?",
        (subject_name,),
    )
    lesson_plan_count = lesson_plan_row["count"] if lesson_plan_row else 0

    # Count textbooks
    textbook_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM textbooks WHERE subject = ?",
        (subject_name,),
    )
    textbook_count = textbook_row["count"] if textbook_row else 0

    # Count batch tasks
    batch_task_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM batch_tasks WHERE subject = ?",
        (subject_name,),
    )
    batch_task_count = batch_task_row["count"] if batch_task_row else 0

    return {
        "template_count": template_count,
        "lesson_plan_count": lesson_plan_count,
        "textbook_count": textbook_count,
        "batch_task_count": batch_task_count,
    }


@router.post("", response_model=SubjectInfo)
async def create_subject(request: SubjectCreateRequest):
    """
    创建自定义学科

    - **name**: 学科名称（唯一）
    - **category**: 分类（university_course 或 basic_subject）
    - **description**: 可选描述
    """
    # Check if subject name already exists
    existing = await db.fetch_one(
        "SELECT id FROM subjects WHERE name = ?",
        (request.name,),
    )
    if existing:
        raise HTTPException(status_code=409, detail="学科名称已存在")

    # Validate category
    valid_categories = ["university_course", "basic_subject"]
    if request.category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"无效的分类，必须是: {', '.join(valid_categories)}",
        )

    subject_id = str(uuid4())
    timestamp = datetime.now().isoformat()

    # Get max sort_order for the category
    max_order_row = await db.fetch_one(
        "SELECT MAX(sort_order) as max_order FROM subjects WHERE category = ?",
        (request.category,),
    )
    sort_order = (max_order_row["max_order"] or 0) + 1 if max_order_row else 1

    await db.execute(
        """
        INSERT INTO subjects (id, name, category, is_preset, sort_order, description, created_at, updated_at)
        VALUES (?, ?, ?, 0, ?, ?, ?, ?)
        """,
        (subject_id, request.name, request.category, sort_order, request.description, timestamp, timestamp),
        commit=True,
    )

    return SubjectInfo(
        id=subject_id,
        name=request.name,
        category=request.category,
        is_preset=False,
        sort_order=sort_order,
        description=request.description,
        created_at=timestamp,
        updated_at=timestamp,
    )


@router.get("", response_model=SubjectListResponse)
async def list_subjects(
    category: Optional[str] = Query(None, description="按分类筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(100, ge=1, le=200, description="每页数量"),
):
    """
    获取学科列表（支持分类筛选和分页）

    - **category**: 可选，按分类筛选（university_course 或 basic_subject）
    - **page**: 页码（默认1）
    - **limit**: 每页数量（默认100，最大200）
    """
    # Build query based on category filter
    if category:
        count_query = "SELECT COUNT(*) as count FROM subjects WHERE category = ?"
        list_query = "SELECT * FROM subjects WHERE category = ? ORDER BY sort_order, name LIMIT ? OFFSET ?"
        count_params = (category,)
        list_params_base = (category,)
    else:
        count_query = "SELECT COUNT(*) as count FROM subjects"
        list_query = "SELECT * FROM subjects ORDER BY category, sort_order, name LIMIT ? OFFSET ?"
        count_params = ()
        list_params_base = ()

    # Get total count
    count_row = await db.fetch_one(count_query, count_params)
    total = count_row["count"] if count_row else 0

    # Get paginated subjects
    offset = (page - 1) * limit
    list_params = list_params_base + (limit, offset)
    rows = await db.fetch_all(list_query, list_params)

    subjects = [
        SubjectInfo(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            is_preset=bool(row["is_preset"]),
            sort_order=row["sort_order"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]

    return SubjectListResponse(subjects=subjects, total=total)


@router.get("/{subject_id}", response_model=SubjectWithUsageStats)
async def get_subject(subject_id: str):
    """
    获取指定学科详情（含使用统计）

    返回学科信息及其在模板、教案、教材、批量任务中的使用统计。
    """
    row = await db.fetch_one(
        "SELECT * FROM subjects WHERE id = ?",
        (subject_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="学科不存在")

    # Get usage statistics
    usage_stats = await get_subject_usage_stats(row["name"])

    return SubjectWithUsageStats(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        is_preset=bool(row["is_preset"]),
        sort_order=row["sort_order"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        usage_stats=usage_stats,
    )


@router.put("/{subject_id}", response_model=SubjectInfo)
async def update_subject(subject_id: str, request: SubjectUpdateRequest):
    """
    更新学科信息

    - 预设学科只能更新description
    - 自定义学科可以更新name和description
    - 如果更新name，必须保证不与其他学科名称冲突
    """
    # Check if exists
    row = await db.fetch_one("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    if not row:
        raise HTTPException(status_code=404, detail="学科不存在")

    is_preset = bool(row["is_preset"])

    # Build update query dynamically
    update_fields = []
    params = []

    # Preset subjects can only update description
    if request.name is not None:
        if is_preset:
            raise HTTPException(
                status_code=403,
                detail="预设学科不能修改名称，只能修改描述信息",
            )
        # Check if new name conflicts with existing subjects
        existing = await db.fetch_one(
            "SELECT id FROM subjects WHERE name = ? AND id != ?",
            (request.name, subject_id),
        )
        if existing:
            raise HTTPException(status_code=409, detail="学科名称已存在")

        update_fields.append("name = ?")
        params.append(request.name)

    if request.description is not None:
        update_fields.append("description = ?")
        params.append(request.description)

    if update_fields:
        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(subject_id)

        await db.execute(
            f"UPDATE subjects SET {', '.join(update_fields)} WHERE id = ?",
            tuple(params),
            commit=True,
        )

    # Return updated subject
    row = await db.fetch_one("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    return SubjectInfo(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        is_preset=bool(row["is_preset"]),
        sort_order=row["sort_order"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/{subject_id}")
async def delete_subject(subject_id: str):
    """
    删除学科

    - 预设学科不能删除
    - 正在使用的学科不能删除（被模板、教案、教材、批量任务使用）
    """
    # Check if exists
    row = await db.fetch_one("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    if not row:
        raise HTTPException(status_code=404, detail="学科不存在")

    # Cannot delete preset subjects
    if bool(row["is_preset"]):
        raise HTTPException(status_code=403, detail="预设学科不能删除")

    # Check if subject is in use
    usage_stats = await get_subject_usage_stats(row["name"])
    total_usage = sum(usage_stats.values())

    if total_usage > 0:
        raise HTTPException(
            status_code=409,
            detail=f"该学科正在被使用（{total_usage}处引用），无法删除。请先清理相关数据。",
        )

    await db.execute("DELETE FROM subjects WHERE id = ?", (subject_id,), commit=True)
    return {"message": "学科删除成功"}
