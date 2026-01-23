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
    SmartAllocationRequest,
    DraftTaskCreateRequest,
    DraftTaskCreateResponse,
    ExportSelectedRequest,
    BatchLessonPlanListResponse,
    LessonPlan,
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

    Uses AI to generate chapters. If chapters_input is provided,
    it is treated as a reference outline for AI to restructure.
    When chapters_input is absent, cached templates may be reused.
    """
    try:
        # Debug logging to identify validation issues
        logger.info(
            f"Chapter split request received: "
            f"course_name={request.course_name} (type: {type(request.course_name).__name__}), "
            f"subject={request.subject} (type: {type(request.subject).__name__}), "
            f"grade={request.grade} (type: {type(request.grade).__name__}), "
            f"total_hours={request.total_hours} (type: {type(request.total_hours).__name__}), "
            f"hours_per_lesson={request.hours_per_lesson} (type: {type(request.hours_per_lesson).__name__})"
        )

        num_lessons = max(1, request.total_hours // request.hours_per_lesson)

        logger.info(
            f"Splitting course '{request.course_name}' into {num_lessons} lessons "
            f"({request.total_hours} hours, {request.hours_per_lesson} hours/lesson)"
        )

        # If user provided chapters, use AI with reference outline (no caching)
        if request.chapters_input and request.chapters_input.strip():
            logger.info("Using AI with reference chapters")
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
                chapters_input=request.chapters_input,
                additional_info=request.additional_info,
            )
            return ChapterSplitResponse(chapters=chapters, total_lessons=len(chapters))

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
            if len(chapters) == num_lessons:
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

                return ChapterSplitResponse(chapters=chapters, total_lessons=len(chapters))

            logger.warning(
                "Cached template count mismatch; ignoring cache "
                f"(expected={num_lessons}, actual={len(chapters)}, id={existing['id']})"
            )

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

        return ChapterSplitResponse(chapters=chapters, total_lessons=len(chapters))

    except ValueError as e:
        logger.error(f"Failed to split chapters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
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
            db = await get_db()

            chapters_input = request.chapters_input.strip() if request.chapters_input else ""
            use_cache = not chapters_input
            num_lessons = max(1, request.total_hours // request.hours_per_lesson)

            # 检查是否有缓存的模板
            if use_cache:
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
                    # 有缓存 - 直接使用章节
                    chapters_json = json.loads(existing["chapters"])
                    chapters = [ChapterInfo(**c) for c in chapters_json]
                    total_lessons = len(chapters)
                    if total_lessons != num_lessons:
                        logger.warning(
                            "Cached template count mismatch; ignoring cache "
                            f"(expected={num_lessons}, actual={total_lessons}, id={existing['id']})"
                        )
                    else:
                        # 发送初始进度
                        yield f"event: progress\ndata: {json.dumps({'current': 0, 'total': total_lessons, 'message': f'准备加载 {total_lessons} 个章节...'}, ensure_ascii=False)}\n\n"

                        # 有缓存且章节数量正确 - 流式返回缓存的章节
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
                            yield f"event: progress\ndata: {json.dumps({'current': idx, 'total': total_lessons, 'message': f'加载第 {idx}/{total_lessons} 个章节'}, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(0.05)  # 小延迟用于视觉反馈
                            yield f"event: chapter\ndata: {json.dumps(chapter.model_dump(), ensure_ascii=False)}\n\n"

                        yield f"event: complete\ndata: {json.dumps({'chapters': [c.model_dump() for c in chapters], 'total_lessons': total_lessons}, ensure_ascii=False)}\n\n"
                        return

            # AI 生成模式 - 流式生成
            # 发送初始进度
            yield f"event: progress\ndata: {json.dumps({'current': 0, 'total': num_lessons, 'message': f'准备生成 {num_lessons} 份教案...'}, ensure_ascii=False)}\n\n"

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
                chapters_input=chapters_input or None,
                additional_info=request.additional_info,
            ):
                chapter_count += 1
                yield f"event: progress\ndata: {json.dumps({'current': chapter_count, 'total': num_lessons, 'message': f'生成第 {chapter_count}/{num_lessons} 个章节'}, ensure_ascii=False)}\n\n"
                yield f"event: chapter\ndata: {json.dumps(chapter.model_dump(), ensure_ascii=False)}\n\n"
                chapters.append(chapter)

            if chapter_count != num_lessons:
                error_msg = f"AI章节数量不匹配：期望 {num_lessons}，实际 {chapter_count}。请重新生成。"
                logger.error(error_msg)
                yield f"event: error\ndata: {json.dumps({'message': error_msg}, ensure_ascii=False)}\n\n"
                return

            if use_cache:
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

            yield f"event: complete\ndata: {json.dumps({'chapters': [c.model_dump() for c in chapters], 'total_lessons': len(chapters)}, ensure_ascii=False)}\n\n"

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


@router.post("/batch/split-chapters-smart-stream")
async def split_chapters_smart_allocation_stream(request: SmartAllocationRequest):
    """
    智能周次分配模式（流式）。

    用户提供章节标题列表，AI智能分配到指定周数的周次教学计划中。
    支持章节跨周、合并等智能策略。

    SSE 事件类型:
    - progress: {"current": 3, "total": 16, "message": "分配第 3/16 周"}
    - chapter: {"lesson_number": 3, "topic": "第3周：...", "content_summary": "...", "key_concepts": [...]}
    - complete: {"chapters": [...], "total_lessons": 16}
    - error: {"message": "错误详情"}
    """
    async def event_generator():
        try:
            # 发送初始进度
            yield f"event: progress\ndata: {json.dumps({'current': 0, 'total': request.total_weeks, 'message': f'准备分配到 {request.total_weeks} 周...'}, ensure_ascii=False)}\n\n"

            # 创建 ChapterSplitter 实例
            splitter = ChapterSplitter(
                provider=settings.ai_provider,
                api_key=settings.get_active_api_key(),
                model=settings.get_active_model(),
            )

            # 流式生成周次分配
            weeks = []
            week_count = 0

            async for week in splitter._generate_smart_allocation_stream(
                course_name=request.course_name,
                subject=request.subject,
                grade=request.grade,
                chapters_input=request.chapters_input,
                total_weeks=request.total_weeks,
                hours_per_week=request.hours_per_week,
                total_hours=request.total_hours,
                additional_info=request.additional_info,
            ):
                week_count += 1
                weeks.append(week)

                # 发送进度更新
                yield f"event: progress\ndata: {json.dumps({'current': week_count, 'total': request.total_weeks, 'message': f'分配第 {week_count}/{request.total_weeks} 周'}, ensure_ascii=False)}\n\n"

                # 发送章节数据
                yield f"event: chapter\ndata: {json.dumps(week.model_dump(), ensure_ascii=False)}\n\n"

            # 保存到缓存（复用 course_chapter_templates 表）
            db = await get_db()

            # 检查是否已存在相同参数的模板
            existing = await db.fetch_one(
                """
                SELECT id FROM course_chapter_templates
                WHERE course_name = ? AND subject = ? AND grade = ?
                AND total_hours = ? AND hours_per_lesson = ?
                """,
                (
                    request.course_name,
                    request.subject,
                    request.grade,
                    request.total_hours,
                    request.hours_per_week,
                )
            )

            if existing:
                # 更新现有记录
                await db.execute(
                    """
                    UPDATE course_chapter_templates
                    SET chapters = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        json.dumps([w.model_dump() for w in weeks], ensure_ascii=False),
                        datetime.now().isoformat(),
                        existing["id"],
                    ),
                    commit=True,
                )
                logger.info(f"Smart allocation updated existing cache: {existing['id']} ({len(weeks)} weeks)")
            else:
                # 插入新记录
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
                        request.hours_per_week,  # 每周课时数
                        json.dumps([w.model_dump() for w in weeks], ensure_ascii=False),
                        0,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                    ),
                    commit=True,
                )
                logger.info(f"Smart allocation cached: {template_id} ({len(weeks)} weeks)")

            # 发送完成事件
            yield f"event: complete\ndata: {json.dumps({'chapters': [w.model_dump() for w in weeks], 'total_lessons': len(weeks)}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Smart allocation stream failed: {str(e)}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
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
        expected_count = max(1, request.total_hours // request.hours_per_lesson)
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

        if total_count != expected_count:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Chapter count mismatch: expected {expected_count}, "
                    f"got {total_count}. Please regenerate chapters with AI."
                )
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

        # Parse class_ids from JSON if present, otherwise set to empty list
        if task_dict.get("class_ids") and task_dict["class_ids"] != "null":
            task_dict["class_ids"] = json.loads(task_dict["class_ids"])
        else:
            task_dict["class_ids"] = []

        # Convert generate_reflection from INTEGER to boolean
        task_dict["generate_reflection"] = bool(task_dict.get("generate_reflection", 0))

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

            # Parse class_ids from JSON if present, otherwise set to empty list
            if task_dict.get("class_ids") and task_dict["class_ids"] != "null":
                task_dict["class_ids"] = json.loads(task_dict["class_ids"])
            else:
                task_dict["class_ids"] = []

            # Convert generate_reflection from INTEGER to boolean
            task_dict["generate_reflection"] = bool(task_dict.get("generate_reflection", 0))

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


# ============================================================================
# Draft Task Endpoints (for lesson plan caching and management)
# ============================================================================


@router.post("/batch/create-draft-task", response_model=DraftTaskCreateResponse)
async def create_draft_task(request: DraftTaskCreateRequest):
    """
    Create a draft task to pre-generate lesson plans without creating documents.

    Draft tasks:
    - Generate all lesson plan content using AI
    - Store lesson plans with status='draft_cached'
    - Do NOT render Word documents
    - Do NOT create ZIP files
    - Allow later editing and selective export

    This is useful for pre-generating content that can be reviewed, edited,
    and selectively published later.
    """
    try:
        task_id = str(uuid4())
        expected_count = max(1, request.total_hours // request.hours_per_lesson)
        total_count = len(request.chapters)

        logger.info(
            f"Creating draft task {task_id}: "
            f"{request.course_name} ({total_count} lesson plans)"
        )

        # Validate chapters
        if total_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Chapters list cannot be empty"
            )

        if total_count != expected_count:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Chapter count mismatch: expected {expected_count}, "
                    f"got {total_count}. Please regenerate chapters with AI."
                )
            )

        if total_count > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot generate more than 100 lesson plans in one draft task"
            )

        # Create task record in database with task_type='draft'
        db = await get_db()
        await db.execute(
            """
            INSERT INTO batch_tasks (
                id, course_name, subject, grade, template_id,
                total_hours, hours_per_lesson, chapters,
                textbook_name, location, online_resources, generate_reflection,
                status, total_count, task_type, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                request.textbook_name or "",
                request.location or "",
                request.online_resources or "",
                1 if request.generate_reflection else 0,
                "pending",
                total_count,
                "draft",  # task_type='draft'
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
            commit=True,
        )

        # Start processing in background with draft mode enabled
        processor = BatchTaskProcessor(
            provider=settings.ai_provider,
            api_key=settings.get_active_api_key(),
            model=settings.get_active_model(),
            hours_per_lesson=request.hours_per_lesson,
        )

        run_in_background(
            processor.process_batch_task(task_id, is_draft_mode=True),
            name=f"draft-task-{task_id}",
        )

        logger.info(f"Draft task {task_id} created and processing started")

        return DraftTaskCreateResponse(
            task_id=task_id,
            status="pending",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create draft task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/tasks/{task_id}/lesson-plans", response_model=BatchLessonPlanListResponse)
async def get_task_lesson_plans(
    task_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Get all lesson plans associated with a batch task.

    Returns detailed lesson plan information including generated content,
    useful for displaying and editing lesson plans in the batch task detail page.
    """
    try:
        db = await get_db()

        # Get task information
        task_row = await db.fetch_one(
            "SELECT * FROM batch_tasks WHERE id = ?",
            (task_id,)
        )

        if not task_row:
            raise HTTPException(status_code=404, detail="Batch task not found")

        task_dict = dict(task_row)
        task_dict["chapters"] = json.loads(task_dict["chapters"])
        task_dict["class_ids"] = json.loads(task_dict.get("class_ids") or "[]")
        task_dict["generate_reflection"] = bool(task_dict.get("generate_reflection", 0))
        task = BatchTask(**task_dict)

        # Get total count of lesson plans for this task
        count_row = await db.fetch_one(
            """
            SELECT COUNT(*) as count FROM batch_lesson_plans
            WHERE batch_task_id = ?
            """,
            (task_id,)
        )
        total = count_row["count"] if count_row else 0

        # Get paginated lesson plan IDs
        offset = (page - 1) * limit
        batch_plan_rows = await db.fetch_all(
            """
            SELECT lesson_plan_id FROM batch_lesson_plans
            WHERE batch_task_id = ?
            ORDER BY lesson_number ASC
            LIMIT ? OFFSET ?
            """,
            (task_id, limit, offset)
        )

        # Fetch full lesson plan details
        lesson_plans = []
        for row in batch_plan_rows:
            plan_row = await db.fetch_one(
                "SELECT * FROM lesson_plans WHERE id = ?",
                (row["lesson_plan_id"],)
            )
            if plan_row:
                lesson_plans.append(LessonPlan(**dict(plan_row)))

        logger.debug(
            f"Retrieved {len(lesson_plans)} lesson plans for task {task_id} "
            f"(page {page}, total {total})"
        )

        return BatchLessonPlanListResponse(
            lesson_plans=lesson_plans,
            total=total,
            task=task,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get lesson plans for task {task_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/tasks/{task_id}/export-selected")
async def export_selected_lesson_plans(
    task_id: str,
    request: ExportSelectedRequest
):
    """
    Export selected lesson plans from a batch task as a ZIP file.

    This allows selective export of specific lesson plans from a draft task,
    useful when you only want to publish certain lesson plans.

    If group_by_document is True, lesson plans will be grouped 2 per document.
    Otherwise, each lesson plan gets its own document.
    """
    try:
        from ..services.lesson_plan_service import LessonPlanService

        lesson_plan_service = LessonPlanService()

        # Use the lesson plan service to batch publish
        zip_path = await lesson_plan_service.batch_publish(
            lesson_plan_ids=request.lesson_plan_ids,
            group_by_document=request.group_by_document
        )

        if not Path(zip_path).exists():
            raise HTTPException(status_code=404, detail="ZIP file not found")

        filename = Path(zip_path).name

        logger.info(f"Serving selected lesson plans export for task {task_id}: {filename}")

        return FileResponse(
            path=str(zip_path),
            filename=filename,
            media_type="application/zip",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to export selected lesson plans for task {task_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
