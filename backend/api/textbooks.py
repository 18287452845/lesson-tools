"""
Textbook management API endpoints.
Handles textbook CRUD, AI chapter generation, and chapter management.
"""
import json
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..models.database import db
from ..models.schemas import (
    TextbookCreateRequest,
    TextbookUpdateRequest,
    TextbookInfo,
    TextbookListResponse,
    TextbookChapterInfo,
    TextbookChapterCreateRequest,
    TextbookChapterBatchCreateRequest,
    TextbookChapterGenerateRequest,
    TextbookChapterGenerateResponse,
)
from ..services.textbook_generator import TextbookChapterGenerator

router = APIRouter(prefix="/textbooks", tags=["textbooks"])


# ============================================================================
# Textbook CRUD Operations
# ============================================================================


@router.post("", response_model=TextbookInfo)
async def create_textbook(request: TextbookCreateRequest):
    """
    创建新教材

    Args:
        request: 教材创建请求（包含名称、ISBN、作者等信息）

    Returns:
        新创建的教材信息
    """
    textbook_id = str(uuid4())
    timestamp = datetime.now().isoformat()

    await db.execute(
        """
        INSERT INTO textbooks (
            id, name, isbn, author, publisher, edition,
            subject, grade, cover_image, description, status,
            use_count, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            textbook_id,
            request.name,
            request.isbn,
            request.author,
            request.publisher,
            request.edition,
            request.subject,
            request.grade,
            request.cover_image,
            request.description,
            "active",  # default status
            0,  # initial use_count
            timestamp,
            timestamp,
        ),
        commit=True,
    )

    return TextbookInfo(
        id=textbook_id,
        name=request.name,
        isbn=request.isbn,
        author=request.author,
        publisher=request.publisher,
        edition=request.edition,
        subject=request.subject,
        grade=request.grade,
        cover_image=request.cover_image,
        description=request.description,
        status="active",
        use_count=0,
        created_at=timestamp,
        updated_at=timestamp,
        chapters=[],
    )


@router.get("", response_model=TextbookListResponse)
async def list_textbooks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    subject: Optional[str] = Query(None, description="学科筛选"),
    grade: Optional[str] = Query(None, description="年级筛选"),
    status: Optional[str] = Query(None, description="状态筛选 (active/inactive)"),
):
    """
    获取教材列表（分页，支持筛选）

    Args:
        page: 页码
        limit: 每页数量
        subject: 学科筛选（可选）
        grade: 年级筛选（可选）
        status: 状态筛选（可选）

    Returns:
        教材列表和总数
    """
    # Build WHERE clause
    where_conditions = []
    params = []

    if subject:
        where_conditions.append("subject = ?")
        params.append(subject)
    if grade:
        where_conditions.append("grade = ?")
        params.append(grade)
    if status:
        where_conditions.append("status = ?")
        params.append(status)

    where_clause = (
        "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    )

    # Get total count
    count_row = await db.fetch_one(
        f"SELECT COUNT(*) as count FROM textbooks {where_clause}",
        tuple(params),
    )
    total = count_row["count"] if count_row else 0

    # Get paginated textbooks
    offset = (page - 1) * limit
    params.extend([limit, offset])

    rows = await db.fetch_all(
        f"""
        SELECT * FROM textbooks
        {where_clause}
        ORDER BY name, created_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params),
    )

    # Fetch chapters for each textbook
    textbooks = []
    for row in rows:
        textbook_dict = dict(row)
        textbook_id = textbook_dict["id"]

        # Fetch chapters
        chapter_rows = await db.fetch_all(
            """
            SELECT * FROM textbook_chapters
            WHERE textbook_id = ?
            ORDER BY sort_order, chapter_number
            """,
            (textbook_id,),
        )

        chapters = []
        for chapter_row in chapter_rows:
            chapter_dict = dict(chapter_row)
            # Parse key_concepts from JSON string
            if chapter_dict.get("key_concepts"):
                try:
                    chapter_dict["key_concepts"] = json.loads(
                        chapter_dict["key_concepts"]
                    )
                except (json.JSONDecodeError, TypeError):
                    chapter_dict["key_concepts"] = []
            else:
                chapter_dict["key_concepts"] = []

            chapters.append(TextbookChapterInfo(**chapter_dict))

        textbook_dict["chapters"] = chapters
        textbooks.append(TextbookInfo(**textbook_dict))

    return TextbookListResponse(textbooks=textbooks, total=total)


@router.get("/{textbook_id}", response_model=TextbookInfo)
async def get_textbook(textbook_id: str):
    """
    获取指定教材详情（包含章节列表）

    Args:
        textbook_id: 教材ID

    Returns:
        教材详细信息
    """
    row = await db.fetch_one(
        "SELECT * FROM textbooks WHERE id = ?",
        (textbook_id,),
    )

    if not row:
        raise HTTPException(status_code=404, detail="教材不存在")

    textbook_dict = dict(row)

    # Fetch chapters
    chapter_rows = await db.fetch_all(
        """
        SELECT * FROM textbook_chapters
        WHERE textbook_id = ?
        ORDER BY sort_order, chapter_number
        """,
        (textbook_id,),
    )

    chapters = []
    for chapter_row in chapter_rows:
        chapter_dict = dict(chapter_row)
        # Parse key_concepts from JSON string
        if chapter_dict.get("key_concepts"):
            try:
                chapter_dict["key_concepts"] = json.loads(chapter_dict["key_concepts"])
            except (json.JSONDecodeError, TypeError):
                chapter_dict["key_concepts"] = []
        else:
            chapter_dict["key_concepts"] = []

        chapters.append(TextbookChapterInfo(**chapter_dict))

    textbook_dict["chapters"] = chapters
    return TextbookInfo(**textbook_dict)


@router.patch("/{textbook_id}", response_model=TextbookInfo)
async def update_textbook(textbook_id: str, request: TextbookUpdateRequest):
    """
    更新教材信息

    Args:
        textbook_id: 教材ID
        request: 更新请求（包含要更新的字段）

    Returns:
        更新后的教材信息
    """
    # Check if exists
    row = await db.fetch_one("SELECT id FROM textbooks WHERE id = ?", (textbook_id,))
    if not row:
        raise HTTPException(status_code=404, detail="教材不存在")

    # Build update query dynamically
    update_fields = []
    params = []

    if request.name is not None:
        update_fields.append("name = ?")
        params.append(request.name)
    if request.isbn is not None:
        update_fields.append("isbn = ?")
        params.append(request.isbn)
    if request.author is not None:
        update_fields.append("author = ?")
        params.append(request.author)
    if request.publisher is not None:
        update_fields.append("publisher = ?")
        params.append(request.publisher)
    if request.edition is not None:
        update_fields.append("edition = ?")
        params.append(request.edition)
    if request.subject is not None:
        update_fields.append("subject = ?")
        params.append(request.subject)
    if request.grade is not None:
        update_fields.append("grade = ?")
        params.append(request.grade)
    if request.cover_image is not None:
        update_fields.append("cover_image = ?")
        params.append(request.cover_image)
    if request.description is not None:
        update_fields.append("description = ?")
        params.append(request.description)
    if request.status is not None:
        update_fields.append("status = ?")
        params.append(request.status)

    if update_fields:
        update_fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(textbook_id)

        await db.execute(
            f"UPDATE textbooks SET {', '.join(update_fields)} WHERE id = ?",
            tuple(params),
            commit=True,
        )

    # Return updated textbook (with chapters)
    return await get_textbook(textbook_id)


@router.delete("/{textbook_id}")
async def delete_textbook(textbook_id: str):
    """
    删除教材（软删除，设置status为inactive）

    Args:
        textbook_id: 教材ID

    Returns:
        删除结果消息
    """
    # Check if exists
    row = await db.fetch_one("SELECT id FROM textbooks WHERE id = ?", (textbook_id,))
    if not row:
        raise HTTPException(status_code=404, detail="教材不存在")

    # Soft delete: set status to inactive
    await db.execute(
        "UPDATE textbooks SET status = ?, updated_at = ? WHERE id = ?",
        ("inactive", datetime.now().isoformat(), textbook_id),
        commit=True,
    )

    return {"message": "教材删除成功"}


# ============================================================================
# Chapter Management
# ============================================================================


@router.post("/{textbook_id}/generate-chapters", response_model=TextbookChapterGenerateResponse)
async def generate_chapters(
    textbook_id: str,
    request: TextbookChapterGenerateRequest,
):
    """
    使用AI生成教材章节大纲（不保存到数据库）

    Args:
        textbook_id: 教材ID
        request: 章节生成请求（教材名称、ISBN等）

    Returns:
        AI生成的章节列表（待用户审核）
    """
    # Check if textbook exists
    textbook_row = await db.fetch_one(
        "SELECT id FROM textbooks WHERE id = ?",
        (textbook_id,),
    )
    if not textbook_row:
        raise HTTPException(status_code=404, detail="教材不存在")

    # Generate chapters using AI
    try:
        generator = TextbookChapterGenerator()
        chapters = await generator.generate_chapters(request)

        return TextbookChapterGenerateResponse(
            chapters=chapters,
            message=f"成功生成 {len(chapters)} 个章节",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI章节生成失败: {str(e)}"
        )


@router.post("/{textbook_id}/chapters", response_model=TextbookInfo)
async def save_chapters(
    textbook_id: str,
    request: TextbookChapterBatchCreateRequest,
):
    """
    批量保存章节到数据库（用户审核后）

    Args:
        textbook_id: 教材ID
        request: 章节批量创建请求（包含章节列表）

    Returns:
        更新后的教材信息（包含新章节）
    """
    # Check if textbook exists
    textbook_row = await db.fetch_one(
        "SELECT id FROM textbooks WHERE id = ?",
        (textbook_id,),
    )
    if not textbook_row:
        raise HTTPException(status_code=404, detail="教材不存在")

    # Delete existing chapters (if any)
    await db.execute(
        "DELETE FROM textbook_chapters WHERE textbook_id = ?",
        (textbook_id,),
        commit=True,
    )

    # Insert new chapters
    timestamp = datetime.now().isoformat()
    for chapter in request.chapters:
        chapter_id = str(uuid4())

        # Convert key_concepts list to JSON string
        key_concepts_json = json.dumps(
            chapter.key_concepts, ensure_ascii=False
        )

        await db.execute(
            """
            INSERT INTO textbook_chapters (
                id, textbook_id, chapter_number, chapter_title,
                content_summary, key_concepts, sort_order,
                hours_required, parent_chapter_id,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chapter_id,
                textbook_id,
                chapter.chapter_number,
                chapter.chapter_title,
                chapter.content_summary,
                key_concepts_json,
                chapter.sort_order,
                chapter.hours_required,
                chapter.parent_chapter_id,
                timestamp,
                timestamp,
            ),
            commit=True,
        )

    # Update textbook's updated_at
    await db.execute(
        "UPDATE textbooks SET updated_at = ? WHERE id = ?",
        (timestamp, textbook_id),
        commit=True,
    )

    # Return updated textbook with chapters
    return await get_textbook(textbook_id)


@router.get("/{textbook_id}/chapters/{chapter_id}", response_model=TextbookChapterInfo)
async def get_chapter(textbook_id: str, chapter_id: str):
    """
    获取指定章节详情

    Args:
        textbook_id: 教材ID
        chapter_id: 章节ID

    Returns:
        章节详细信息
    """
    row = await db.fetch_one(
        """
        SELECT * FROM textbook_chapters
        WHERE id = ? AND textbook_id = ?
        """,
        (chapter_id, textbook_id),
    )

    if not row:
        raise HTTPException(status_code=404, detail="章节不存在")

    chapter_dict = dict(row)

    # Parse key_concepts from JSON string
    if chapter_dict.get("key_concepts"):
        try:
            chapter_dict["key_concepts"] = json.loads(chapter_dict["key_concepts"])
        except (json.JSONDecodeError, TypeError):
            chapter_dict["key_concepts"] = []
    else:
        chapter_dict["key_concepts"] = []

    return TextbookChapterInfo(**chapter_dict)


@router.patch("/{textbook_id}/chapters/{chapter_id}", response_model=TextbookChapterInfo)
async def update_chapter(
    textbook_id: str,
    chapter_id: str,
    request: TextbookChapterCreateRequest,
):
    """
    更新章节信息

    Args:
        textbook_id: 教材ID
        chapter_id: 章节ID
        request: 章节更新请求

    Returns:
        更新后的章节信息
    """
    # Check if chapter exists
    row = await db.fetch_one(
        "SELECT id FROM textbook_chapters WHERE id = ? AND textbook_id = ?",
        (chapter_id, textbook_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="章节不存在")

    # Convert key_concepts list to JSON string
    key_concepts_json = json.dumps(request.key_concepts, ensure_ascii=False)

    # Update chapter
    timestamp = datetime.now().isoformat()
    await db.execute(
        """
        UPDATE textbook_chapters SET
            chapter_number = ?,
            chapter_title = ?,
            content_summary = ?,
            key_concepts = ?,
            sort_order = ?,
            hours_required = ?,
            parent_chapter_id = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            request.chapter_number,
            request.chapter_title,
            request.content_summary,
            key_concepts_json,
            request.sort_order,
            request.hours_required,
            request.parent_chapter_id,
            timestamp,
            chapter_id,
        ),
        commit=True,
    )

    # Return updated chapter
    return await get_chapter(textbook_id, chapter_id)


@router.delete("/{textbook_id}/chapters/{chapter_id}")
async def delete_chapter(textbook_id: str, chapter_id: str):
    """
    删除章节

    Args:
        textbook_id: 教材ID
        chapter_id: 章节ID

    Returns:
        删除结果消息
    """
    # Check if chapter exists
    row = await db.fetch_one(
        "SELECT id FROM textbook_chapters WHERE id = ? AND textbook_id = ?",
        (chapter_id, textbook_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="章节不存在")

    await db.execute(
        "DELETE FROM textbook_chapters WHERE id = ?",
        (chapter_id,),
        commit=True,
    )

    return {"message": "章节删除成功"}
