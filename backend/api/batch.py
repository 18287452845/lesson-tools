"""
Batch lesson plan generation API endpoints.

Updated to support hours-based generation instead of week-based.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
import asyncio

from ..config import settings
from ..models.database import get_db
from ..models.schemas import (
    ChapterSplitRequest,
    ChapterSplitResponse,
    BatchTaskCreateRequest,
    BatchTaskCreateResponse,
    BatchTask,
    BatchTaskListResponse,
    ChapterInfo,
    CourseChapterTemplate,
    ChapterTemplateListResponse,
)
from ..services.chapter_splitter import ChapterSplitter
from ..services.batch_processor import BatchTaskProcessor
from ..services.background_runner import run_in_background

logger = logging.getLogger(__name__)

router = APIRouter(tags=["batch"])


@router.post("/batch/split-chapters", response_model=ChapterSplitResponse)
async def split_chapters(request: ChapterSplitRequest):
    """
    Generate lesson plan chapters based on total hours.

    Supports two modes:
    - If chapters_input is provided: Parse user-provided chapter titles
    - Otherwise: AI generates chapters automatically

    Also checks for cached templates to avoid regeneration.
    """
    try:
        num_lessons = request.total_hours // request.hours_per_lesson

        logger.info(
            f"Splitting course '{request.course_name}' into {num_lessons} lessons "
            f"({request.total_hours} hours, {request.hours_per_lesson} hours/lesson)"
        )

        # If user provided chapters, parse them directly (no caching)
        if request.chapters_input and request.chapters_input.strip():
            logger.info("Using user-provided chapters")
            splitter = ChapterSplitter()
            chapters = await splitter.split_course_chapters(
                course_name=request.course_name,
                subject=request.subject,
                grade=request.grade,
                total_hours=request.total_hours,
                hours_per_lesson=request.hours_per_lesson,
                chapters_input=request.chapters_input,
                additional_info=request.additional_info,
            )
            return ChapterSplitResponse(chapters=chapters, total_lessons=num_lessons)

        # Step 1: Check if template exists in database
        db = await get_db()
        existing = await db.fetch_one(
            """
            SELECT * FROM course_chapter_templates
            WHERE course_name = ? AND subject = ? AND grade = ?
            AND total_hours = ? AND hours_per_lesson = ?
            """,
            (
                request.course_name,
                request.subject,
                request.grade,
                request.total_hours,
                request.hours_per_lesson,
            )
        )

        if existing:
            # Found cached template
            chapters_json = json.loads(existing["chapters"])
            chapters = [ChapterInfo(**c) for c in chapters_json]

            # Increment use count
            await db.execute(
                """
                UPDATE course_chapter_templates
                SET use_count = use_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), existing["id"]),
                commit=True,
            )

            logger.info(
                f"Using cached template (id={existing['id']}, "
                f"use_count={existing['use_count'] + 1})"
            )

            return ChapterSplitResponse(chapters=chapters, total_lessons=num_lessons)

        # Step 2: No cached template, call AI to generate
        logger.info("No cached template found, calling AI...")

        splitter = ChapterSplitter(
            provider=settings.ai_provider,
            api_key=settings.get_active_api_key(),
            model=settings.get_active_model(),
        )

        chapters = await splitter.split_course_chapters(
            course_name=request.course_name,
            subject=request.subject,
            grade=request.grade,
            total_hours=request.total_hours,
            hours_per_lesson=request.hours_per_lesson,
            additional_info=request.additional_info,
        )

        # Step 3: Save to database for future use
        template_id = str(uuid4())
        await db.execute(
            """
            INSERT INTO course_chapter_templates (
                id, course_name, subject, grade, total_hours, hours_per_lesson,
                chapters, use_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                request.course_name,
                request.subject,
                request.grade,
                request.total_hours,
                request.hours_per_lesson,
                json.dumps([c.model_dump() for c in chapters], ensure_ascii=False),
                0,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
            commit=True,
        )

        logger.info(
            f"Successfully generated and cached {len(chapters)} chapters "
            f"(template_id={template_id})"
        )

        return ChapterSplitResponse(chapters=chapters, total_lessons=num_lessons)

    except Exception as e:
        logger.error(f"Failed to split chapters: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/split-chapters-stream")
async def split_chapters_stream(request: ChapterSplitRequest):
    """
    流式生成章节，使用 Server-Sent Events (SSE) 返回进度。

    SSE 事件类型:
    - progress: {"current": 3, "total": 16, "message": "生成第 3/16 个章节"}
    - chapter: {"lesson_number": 3, "topic": "...", "content_summary": "...", "key_concepts": [...]}
    - complete: {"chapters": [...], "total_lessons": 16}
    - error: {"message": "错误详情"}
    """
    async def event_generator():
        try:
            num_lessons = request.total_hours // request.hours_per_lesson

            # 发送初始进度
            yield f"event: progress\ndata: {json.dumps({'current': 0, 'total': num_lessons, 'message': f'准备生成 {num_lessons} 份教案...'}, ensure_ascii=False)}\n\n"

            db = await get_db()

            # 如果用户提供了章节输入，直接解析（不缓存）
            if request.chapters_input and request.chapters_input.strip():
                splitter = ChapterSplitter()
                chapters = await splitter.split_course_chapters(
                    course_name=request.course_name,
                    subject=request.subject,
                    grade=request.grade,
                    total_hours=request.total_hours,
                    hours_per_lesson=request.hours_per_lesson,
                    chapters_input=request.chapters_input,
                    additional_info=request.additional_info,
                )

                # 流式返回解析的章节
                for idx, chapter in enumerate(chapters, 1):
                    yield f"event: progress\ndata: {json.dumps({'current': idx, 'total': num_lessons, 'message': f'解析第 {idx}/{num_lessons} 个章节'}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.02)  # 小延迟用于视觉反馈
                    yield f"event: chapter\ndata: {json.dumps(chapter.model_dump(), ensure_ascii=False)}\n\n"

                yield f"event: complete\ndata: {json.dumps({'chapters': [c.model_dump() for c in chapters], 'total_lessons': num_lessons}, ensure_ascii=False)}\n\n"
                return

            # 检查是否有缓存的模板
            existing = await db.fetch_one(
                """
                SELECT * FROM course_chapter_templates
                WHERE course_name = ? AND subject = ? AND grade = ?
                AND total_hours = ? AND hours_per_lesson = ?
                """,
                (
                    request.course_name,
                    request.subject,
                    request.grade,
                    request.total_hours,
                    request.hours_per_lesson,
                )
            )

            if existing:
                # 有缓存 - 流式返回缓存的章节
                chapters_json = json.loads(existing["chapters"])
                chapters = [ChapterInfo(**c) for c in chapters_json]

                # 更新使用计数
                await db.execute(
                    """
                    UPDATE course_chapter_templates
                    SET use_count = use_count + 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (datetime.now().isoformat(), existing["id"]),
                    commit=True,
                )

                # 模拟进度流式返回
                for idx, chapter in enumerate(chapters, 1):
                    yield f"event: progress\ndata: {json.dumps({'current': idx, 'total': num_lessons, 'message': f'加载第 {idx}/{num_lessons} 个章节'}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)  # 小延迟用于视觉反馈
                    yield f"event: chapter\ndata: {json.dumps(chapter.model_dump(), ensure_ascii=False)}\n\n"

                yield f"event: complete\ndata: {json.dumps({'chapters': [c.model_dump() for c in chapters], 'total_lessons': num_lessons}, ensure_ascii=False)}\n\n"
                return

            # AI 生成模式 - 流式生成
            splitter = ChapterSplitter(
                provider=settings.ai_provider,
                api_key=settings.get_active_api_key(),
                model=settings.get_active_model(),
            )

            chapters = []
            chapter_count = 0

            async for chapter in splitter._generate_ai_chapters_stream(
                course_name=request.course_name,
                subject=request.subject,
                grade=request.grade,
                total_hours=request.total_hours,
                hours_per_lesson=request.hours_per_lesson,
                num_lessons=num_lessons,
                additional_info=request.additional_info,
            ):
                chapter_count += 1
                yield f"event: progress\ndata: {json.dumps({'current': chapter_count, 'total': num_lessons, 'message': f'生成第 {chapter_count}/{num_lessons} 个章节'}, ensure_ascii=False)}\n\n"
                yield f"event: chapter\ndata: {json.dumps(chapter.model_dump(), ensure_ascii=False)}\n\n"
                chapters.append(chapter)

            # 保存到数据库
            template_id = str(uuid4())
            await db.execute(
                """
                INSERT INTO course_chapter_templates (
                    id, course_name, subject, grade, total_hours, hours_per_lesson,
                    chapters, use_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    request.course_name,
                    request.subject,
                    request.grade,
                    request.total_hours,
                    request.hours_per_lesson,
                    json.dumps([c.model_dump() for c in chapters], ensure_ascii=False),
                    0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
                commit=True,
            )

            yield f"event: complete\ndata: {json.dumps({'chapters': [c.model_dump() for c in chapters[:num_lessons]], 'total_lessons': num_lessons}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Stream chapter generation failed: {str(e)}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )


@router.post("/batch/create-task", response_model=BatchTaskCreateResponse)
async def create_batch_task(request: BatchTaskCreateRequest):
    """
    Create a batch lesson plan generation task and start processing.

    The task will run in the background. Use the returned task_id
    to check progress via GET /batch/tasks/{task_id}.
    """
    try:
        task_id = str(uuid4())
        total_count = len(request.chapters)

        logger.info(
            f"Creating batch task {task_id}: "
            f"{request.course_name} ({total_count} lesson plans, "
            f"{request.total_hours} hours)"
        )

        # Validate chapters
        if total_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Chapters list cannot be empty"
            )

        if total_count > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot generate more than 100 lesson plans in one batch"
            )

        # Query class names from class_ids
        db = await get_db()
        class_names = []
        if request.class_ids:
            placeholders = ",".join(["?"] * len(request.class_ids))
            class_rows = await db.fetch_all(
                f"SELECT name FROM classes WHERE id IN ({placeholders})",
                tuple(request.class_ids)
            )
            class_names = [row["name"] for row in class_rows]

        # Create task record in database
        await db.execute(
            """
            INSERT INTO batch_tasks (
                id, course_name, subject, grade, template_id,
                total_hours, hours_per_lesson, chapters, start_week, class_ids,
                location, textbook_name, online_resources, generate_reflection, class_names,
                status, total_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                request.course_name,
                request.subject,
                request.grade,
                request.template_id,
                request.total_hours,
                request.hours_per_lesson,
                json.dumps([c.model_dump() for c in request.chapters], ensure_ascii=False),
                request.start_week,
                json.dumps(request.class_ids, ensure_ascii=False),
                request.location or "",
                request.textbook_name or "",
                request.online_resources or "",
                1 if request.generate_reflection else 0,
                ",".join(class_names) if class_names else "",
                "pending",
                total_count,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
            commit=True,
        )

        # Start processing in background
        processor = BatchTaskProcessor(
            provider=settings.ai_provider,
            api_key=settings.get_active_api_key(),
            model=settings.get_active_model(),
            hours_per_lesson=request.hours_per_lesson,
        )

        run_in_background(
            processor.process_batch_task(task_id),
            name=f"batch-task-{task_id}",
        )

        logger.info(f"Batch task {task_id} created and processing started")

        return BatchTaskCreateResponse(
            task_id=task_id,
            status="pending",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create batch task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/tasks/{task_id}", response_model=BatchTask)
async def get_batch_task(task_id: str):
    """
    Get the status and details of a batch task.

    Used for polling task progress from the frontend.
    """
    try:
        db = await get_db()
        row = await db.fetch_one(
            "SELECT * FROM batch_tasks WHERE id = ?",
            (task_id,)
        )

        if not row:
            raise HTTPException(status_code=404, detail="Batch task not found")

        task_dict = dict(row)

        # Parse chapters JSON
        task_dict["chapters"] = json.loads(task_dict["chapters"])

        return BatchTask(**task_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch task {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/tasks", response_model=BatchTaskListResponse)
async def list_batch_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    List all batch tasks with optional filtering and pagination.
    """
    try:
        db = await get_db()

        # Build query
        where_clause = ""
        params = []

        if status:
            where_clause = "WHERE status = ?"
            params.append(status)

        # Get total count
        count_sql = f"SELECT COUNT(*) as count FROM batch_tasks {where_clause}"
        count_row = await db.fetch_one(count_sql, tuple(params))
        total = count_row["count"] if count_row else 0

        # Get paginated tasks
        offset = (page - 1) * limit
        tasks_sql = f"""
            SELECT * FROM batch_tasks
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = await db.fetch_all(tasks_sql, tuple(params))

        tasks = []
        for row in rows:
            task_dict = dict(row)
            # Parse chapters JSON
            task_dict["chapters"] = json.loads(task_dict["chapters"])
            tasks.append(BatchTask(**task_dict))

        logger.debug(f"Listed {len(tasks)} batch tasks (page {page}, total {total})")

        return BatchTaskListResponse(
            tasks=tasks,
            total=total,
        )

    except Exception as e:
        logger.error(f"Failed to list batch tasks: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/tasks/{task_id}/download")
async def download_batch_zip(task_id: str):
    """
    Download the ZIP file containing all generated lesson plans.

    Only works if the task status is 'completed'.
    """
    try:
        db = await get_db()
        row = await db.fetch_one(
            "SELECT * FROM batch_tasks WHERE id = ?",
            (task_id,)
        )

        if not row:
            raise HTTPException(status_code=404, detail="Batch task not found")

        task = dict(row)

        if task["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Task is not completed yet (status: {task['status']})"
            )

        zip_file_path = task.get("zip_file_path")
        if not zip_file_path:
            raise HTTPException(
                status_code=404,
                detail="ZIP file path not found in task record"
            )

        zip_path = Path(zip_file_path)
        if not zip_path.exists():
            raise HTTPException(
                status_code=404,
                detail="ZIP file not found on disk"
            )

        # Extract filename for download
        filename = zip_path.name

        logger.info(f"Serving ZIP download for task {task_id}: {filename}")

        return FileResponse(
            path=str(zip_path),
            filename=filename,
            media_type="application/zip",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to download batch ZIP {task_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batch/tasks/{task_id}")
async def delete_batch_task(task_id: str):
    """
    Delete or cancel a batch task.

    - If task is pending/processing: Sets status to 'cancelled'
    - If task is completed/failed: Deletes the task and optionally the ZIP file
    """
    try:
        db = await get_db()
        row = await db.fetch_one(
            "SELECT * FROM batch_tasks WHERE id = ?",
            (task_id,)
        )

        if not row:
            raise HTTPException(status_code=404, detail="Batch task not found")

        task = dict(row)
        status = task["status"]

        if status in ["pending", "processing"]:
            # Cancel the task
            await db.execute(
                """
                UPDATE batch_tasks
                SET status = 'cancelled', updated_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), task_id),
                commit=True,
            )
            logger.info(f"Cancelled batch task {task_id}")
            return {"message": "Task cancelled", "task_id": task_id}

        else:
            # Delete completed/failed task
            # Optionally delete ZIP file
            zip_file_path = task.get("zip_file_path")
            if zip_file_path:
                zip_path = Path(zip_file_path)
                if zip_path.exists():
                    zip_path.unlink()
                    logger.info(f"Deleted ZIP file: {zip_path}")

            # Delete related batch_lesson_plans records
            await db.execute(
                "DELETE FROM batch_lesson_plans WHERE batch_task_id = ?",
                (task_id,),
                commit=True,
            )

            # Delete the task
            await db.execute(
                "DELETE FROM batch_tasks WHERE id = ?",
                (task_id,),
                commit=True,
            )

            logger.info(f"Deleted batch task {task_id}")
            return {"message": "Task deleted", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete batch task {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/chapter-templates", response_model=ChapterTemplateListResponse)
async def list_chapter_templates(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """
    List all cached course chapter templates.

    Returns templates sorted by use count (most used first), then by created date (newest first).
    """
    try:
        db = await get_db()

        # Get total count
        count_row = await db.fetch_one("SELECT COUNT(*) as count FROM course_chapter_templates")
        total = count_row["count"] if count_row else 0

        # Get paginated templates
        offset = (page - 1) * limit
        rows = await db.fetch_all(
            """
            SELECT * FROM course_chapter_templates
            ORDER BY use_count DESC, created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )

        templates = []
        for row in rows:
            template_dict = dict(row)
            # Parse chapters JSON
            template_dict["chapters"] = json.loads(template_dict["chapters"])
            templates.append(CourseChapterTemplate(**template_dict))

        logger.debug(f"Listed {len(templates)} chapter templates (page {page}, total {total})")

        return ChapterTemplateListResponse(
            templates=templates,
            total=total,
        )

    except Exception as e:
        logger.error(f"Failed to list chapter templates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
