"""
Grade management API endpoints.
Full CRUD operations for managing grades with usage statistics and preset protection.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query

from ..models.database import db
from ..models.schemas import (
    GradeCreateRequest,
    GradeUpdateRequest,
    GradeInfo,
    GradeListResponse,
    GradeWithUsageStats,
)

router = APIRouter(prefix="/grades", tags=["grades"])


async def get_grade_usage_stats(grade_name: str) -> dict:
    """Calculate usage statistics for a grade."""
    # Count templates
    template_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM templates WHERE grade = ?",
        (grade_name,),
    )
    template_count = template_row["count"] if template_row else 0

    # Count lesson plans
    lesson_plan_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM lesson_plans WHERE grade = ?",
        (grade_name,),
    )
    lesson_plan_count = lesson_plan_row["count"] if lesson_plan_row else 0

    # Count textbooks
    textbook_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM textbooks WHERE grade = ?",
        (grade_name,),
    )
    textbook_count = textbook_row["count"] if textbook_row else 0

    # Count batch tasks
    batch_task_row = await db.fetch_one(
        "SELECT COUNT(*) as count FROM batch_tasks WHERE grade = ?",
        (grade_name,),
    )
    batch_task_count = batch_task_row["count"] if batch_task_row else 0

    return {
        "template_count": template_count,
        "lesson_plan_count": lesson_plan_count,
        "textbook_count": textbook_count,
        "batch_task_count": batch_task_count,
    }


@router.post("", response_model=GradeInfo)
async def create_grade(request: GradeCreateRequest):
    """
    创建自定义年级

    - **name**: 年级名称（唯一）
    - **category**: 分类（university, high_school, middle_school, 或 elementary）
    - **description**: 可选描述
    """
    # Check if grade name already exists
    existing = await db.fetch_one(
        "SELECT id FROM grades WHERE name = ?",
        (request.name,),
    )
    if existing:
        raise HTTPException(status_code=409, detail="年级名称已存在")

    # Validate category
    valid_categories = ["university", "high_school", "middle_school", "elementary"]
    if request.category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"无效的分类，必须是: {', '.join(valid_categories)}",
        )

    grade_id = str(uuid4())
    timestamp = datetime.now().isoformat()

    # Get max sort_order for the category
    max_order_row = await db.fetch_one(
        "SELECT MAX(sort_order) as max_order FROM grades WHERE category = ?",
        (request.category,),
    )
    sort_order = (max_order_row["max_order"] or 0) + 1 if max_order_row else 1

    await db.execute(
        """
        INSERT INTO grades (id, name, category, is_preset, sort_order, description, created_at, updated_at)
        VALUES (?, ?, ?, 0, ?, ?, ?, ?)
        """,
        (grade_id, request.name, request.category, sort_order, request.description, timestamp, timestamp),
        commit=True,
    )

    return GradeInfo(
        id=grade_id,
        name=request.name,
        category=request.category,
        is_preset=False,
        sort_order=sort_order,
        description=request.description,
        created_at=timestamp,
        updated_at=timestamp,
    )


@router.get("", response_model=GradeListResponse)
async def list_grades(
    category: Optional[str] = Query(None, description="按分类筛选"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(100, ge=1, le=200, description="每页数量"),
):
    """
    获取年级列表（支持分类筛选和分页）

    - **category**: 可选，按分类筛选（university, high_school, middle_school, 或 elementary）
    - **page**: 页码（默认1）
    - **limit**: 每页数量（默认100，最大200）
    """
    # Build query based on category filter
    if category:
        count_query = "SELECT COUNT(*) as count FROM grades WHERE category = ?"
        list_query = "SELECT * FROM grades WHERE category = ? ORDER BY sort_order, name LIMIT ? OFFSET ?"
        count_params = (category,)
        list_params_base = (category,)
    else:
        count_query = "SELECT COUNT(*) as count FROM grades"
        list_query = "SELECT * FROM grades ORDER BY category, sort_order, name LIMIT ? OFFSET ?"
        count_params = ()
        list_params_base = ()

    # Get total count
    count_row = await db.fetch_one(count_query, count_params)
    total = count_row["count"] if count_row else 0

    # Get paginated grades
    offset = (page - 1) * limit
    list_params = list_params_base + (limit, offset)
    rows = await db.fetch_all(list_query, list_params)

    grades = [
        GradeInfo(
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

    return GradeListResponse(grades=grades, total=total)


@router.get("/{grade_id}", response_model=GradeWithUsageStats)
async def get_grade(grade_id: str):
    """
    获取指定年级详情（含使用统计）

    返回年级信息及其在模板、教案、教材、批量任务中的使用统计。
    """
    row = await db.fetch_one(
        "SELECT * FROM grades WHERE id = ?",
        (grade_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="年级不存在")

    # Get usage statistics
    usage_stats = await get_grade_usage_stats(row["name"])

    return GradeWithUsageStats(
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


@router.put("/{grade_id}", response_model=GradeInfo)
async def update_grade(grade_id: str, request: GradeUpdateRequest):
    """
    更新年级信息

    - 预设年级只能更新description
    - 自定义年级可以更新name和description
    - 如果更新name，必须保证不与其他年级名称冲突
    """
    # Check if exists
    row = await db.fetch_one("SELECT * FROM grades WHERE id = ?", (grade_id,))
    if not row:
        raise HTTPException(status_code=404, detail="年级不存在")

    is_preset = bool(row["is_preset"])

    # Build update query dynamically
    update_fields = []
    params = []

    # Preset grades can only update description
    if request.name is not None:
        if is_preset:
            raise HTTPException(
                status_code=403,
                detail="预设年级不能修改名称，只能修改描述信息",
            )
        # Check if new name conflicts with existing grades
        existing = await db.fetch_one(
            "SELECT id FROM grades WHERE name = ? AND id != ?",
            (request.name, grade_id),
        )
        if existing:
            raise HTTPException(status_code=409, detail="年级名称已存在")

        update_fields.append("name = ?")
        params.append(request.name)

    if request.description is not None:
        update_fields.append("description = ?")
        params.append(request.description)

    if update_fields:
        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(grade_id)

        await db.execute(
            f"UPDATE grades SET {', '.join(update_fields)} WHERE id = ?",
            tuple(params),
            commit=True,
        )

    # Return updated grade
    row = await db.fetch_one("SELECT * FROM grades WHERE id = ?", (grade_id,))
    return GradeInfo(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        is_preset=bool(row["is_preset"]),
        sort_order=row["sort_order"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/{grade_id}")
async def delete_grade(grade_id: str):
    """
    删除年级

    - 预设年级不能删除
    - 正在使用的年级不能删除（被模板、教案、教材、批量任务使用）
    """
    # Check if exists
    row = await db.fetch_one("SELECT * FROM grades WHERE id = ?", (grade_id,))
    if not row:
        raise HTTPException(status_code=404, detail="年级不存在")

    # Cannot delete preset grades
    if bool(row["is_preset"]):
        raise HTTPException(status_code=403, detail="预设年级不能删除")

    # Check if grade is in use
    usage_stats = await get_grade_usage_stats(row["name"])
    total_usage = sum(usage_stats.values())

    if total_usage > 0:
        raise HTTPException(
            status_code=409,
            detail=f"该年级正在被使用（{total_usage}处引用），无法删除。请先清理相关数据。",
        )

    await db.execute("DELETE FROM grades WHERE id = ?", (grade_id,), commit=True)
    return {"message": "年级删除成功"}
