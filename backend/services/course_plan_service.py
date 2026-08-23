"""
Course Plan Service

Builds standalone semester plans (Yunlin teaching/experiment plan tables)
from already generated lesson plans:
- Derives per-lesson rows from lesson-plan content (generated + final overlay)
- Generates compliant experiment names via AI (two lessons per experiment)
- Persists editable drafts and renders fixed-template documents on export
"""
import json
import logging
import zipfile
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ..config import settings
from ..models.database import get_db
from ..models.schemas import (
    COURSE_PLAN_MAX_GROUPS,
    COURSE_PLAN_MAX_LESSONS,
    CoursePlanChapter,
    CoursePlanCreateRequest,
    CoursePlanDetail,
    CoursePlanListItem,
    CoursePlanUpdateRequest,
)
from ..utils.ai_config import get_user_ai_config
from .course_plan_renderer import (
    CoursePlanRenderer,
    require_valid_course_plan_template,
)
from .experiment_names import ensure_experiment_names, validate_experiment_chapters
from .background_runner import run_in_background
from .lesson_content import merge_lesson_content
from .point_briefs import ensure_brief_points

logger = logging.getLogger(__name__)

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
ZIP_MEDIA_TYPE = "application/zip"


class CoursePlanTemplateError(Exception):
    """A fixed course-plan template asset failed validation."""


def _group_count(lesson_count: int) -> int:
    return (lesson_count + 1) // 2


def _as_text(value: Any) -> str:
    """Flatten list content into single-line text for template cells."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


class CoursePlanService:
    """Manage standalone semester-plan drafts and their exports."""

    def __init__(self, course_plan_renderer: Optional[CoursePlanRenderer] = None):
        self.course_plan_renderer = course_plan_renderer or CoursePlanRenderer()

    # ------------------------------------------------------------------ create

    async def create_draft(self, request: CoursePlanCreateRequest) -> CoursePlanDetail:
        """Persist the draft immediately and condense via AI in the background.

        The site proxy cuts connections after ~120s while AI condensation of a
        full course takes 1-3 minutes, so no AI is awaited on the request path.
        """
        chapters = await self._build_chapters(request.lesson_plan_ids)
        self._check_capacity(chapters)
        if "experiment_plan" in request.plan_types:
            self._check_experiment_metadata(
                plan_date=request.plan_date,
                first_class_date=request.first_class_date,
                class_periods=request.class_periods,
                class_names=request.class_names,
                class_schedules=[
                    schedule.model_dump() for schedule in request.class_schedules
                ],
            )

        total_hours = request.total_hours or len(chapters) * request.hours_per_lesson
        course_plan_id = str(uuid4())
        now = datetime.now().isoformat()
        db = await get_db()
        await db.execute(
            """
            INSERT INTO course_plans (
                id, course_name, grade, class_names, academic_year, semester,
                teacher_name, hours_per_lesson, start_week, total_hours, location,
                plan_date, first_class_date, class_periods, class_schedules,
                plan_types, chapters, source_lesson_plan_ids, status,
                output_files, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                course_plan_id,
                request.course_name.strip(),
                request.grade.strip(),
                ",".join(request.class_names),
                request.academic_year.strip(),
                request.semester,
                request.teacher_name.strip(),
                request.hours_per_lesson,
                request.start_week,
                total_hours,
                (request.location or "").strip(),
                (request.plan_date or "").strip(),
                (request.first_class_date or "").strip(),
                (request.class_periods or "").strip(),
                json.dumps(
                    [schedule.model_dump() for schedule in request.class_schedules],
                    ensure_ascii=False,
                ),
                json.dumps(request.plan_types, ensure_ascii=False),
                json.dumps(chapters, ensure_ascii=False),
                json.dumps(request.lesson_plan_ids, ensure_ascii=False),
                "condensing",
                "[]",
                now,
                now,
            ),
            commit=True,
        )
        logger.info(
            "Created course plan draft %s with %s lessons (%s), condensing in background",
            course_plan_id,
            len(chapters),
            "、".join(request.plan_types),
        )
        run_in_background(
            self._finalize_draft(course_plan_id),
            name=f"course-plan-condense-{course_plan_id[:8]}",
        )
        return await self.get_course_plan(course_plan_id)  # type: ignore[return-value]

    async def _finalize_draft(self, course_plan_id: str) -> None:
        """Condense points and generate experiment names, then unlock the draft."""
        plan = await self.get_course_plan(course_plan_id)
        if not plan:
            return
        chapters = [chapter.model_dump() for chapter in plan.chapters]
        db = await get_db()
        try:
            provider, api_key, model = await get_user_ai_config()
            brief_coro = ensure_brief_points(
                chapters, provider=provider, api_key=api_key, model=model
            )
            if "experiment_plan" in plan.plan_types:
                names_coro = ensure_experiment_names(
                    chapters,
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    require_every_group=True,
                )
                (brief_chapters, _), (named_chapters, _regenerated) = (
                    await asyncio.gather(brief_coro, names_coro)
                )
                brief_by_number = {
                    int(chapter.get("lesson_number") or 0): chapter
                    for chapter in brief_chapters
                }
                chapters = [
                    {
                        **chapter,
                        "key_points": brief_by_number[
                            int(chapter.get("lesson_number") or 0)
                        ]["key_points"],
                        "difficult_points": brief_by_number[
                            int(chapter.get("lesson_number") or 0)
                        ]["difficult_points"],
                    }
                    for chapter in named_chapters
                ]
            else:
                chapters, _ = await brief_coro
            await db.execute(
                """
                UPDATE course_plans
                SET chapters = ?, status = 'draft', error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(chapters, ensure_ascii=False),
                    datetime.now().isoformat(),
                    course_plan_id,
                ),
                commit=True,
            )
            logger.info("Course plan %s condensation finished", course_plan_id)
        except Exception as exc:
            logger.error(
                "Course plan %s condensation failed: %s", course_plan_id, exc
            )
            await db.execute(
                """
                UPDATE course_plans
                SET status = 'draft', error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (str(exc), datetime.now().isoformat(), course_plan_id),
                commit=True,
            )

    async def _build_chapters(self, lesson_plan_ids: List[str]) -> List[Dict[str, Any]]:
        db = await get_db()
        chapters: List[Dict[str, Any]] = []
        for lesson_number, lesson_plan_id in enumerate(lesson_plan_ids, start=1):
            row = await db.fetch_one(
                """
                SELECT id, title, topic, input_data, generated_content, final_content
                FROM lesson_plans WHERE id = ?
                """,
                (lesson_plan_id,),
            )
            if not row:
                raise ValueError(f"教案 {lesson_plan_id} 不存在")
            content = merge_lesson_content(
                row["generated_content"],
                row["final_content"],
                label=f"第 {lesson_number} 份教案",
            )
            if not content:
                topic = (row["topic"] or row["title"] or "").strip()
                raise ValueError(f"教案《{topic}》还没有生成内容，无法用于学期计划")
            topic = (row["topic"] or row["title"] or "").strip()
            if not topic:
                try:
                    input_data = json.loads(row["input_data"]) if row["input_data"] else {}
                except json.JSONDecodeError:
                    input_data = {}
                topic = str(
                    input_data.get("topic")
                    or input_data.get("teaching_topic")
                    or f"第 {lesson_number} 课"
                ).strip()
            chapters.append(
                {
                    "lesson_number": lesson_number,
                    "topic": topic,
                    "key_points": _as_text(content.get("key_points")),
                    "difficult_points": _as_text(content.get("difficult_points")),
                    "homework": content.get("homework"),
                    "experiment_name": "",
                }
            )
        return chapters

    @staticmethod
    def _check_capacity(chapters: List[Dict[str, Any]]) -> None:
        groups = _group_count(len(chapters))
        if groups > COURSE_PLAN_MAX_GROUPS:
            raise ValueError(
                f"固定模板最多容纳 {COURSE_PLAN_MAX_GROUPS} 周（{COURSE_PLAN_MAX_LESSONS} 份教案），"
                f"当前为 {groups} 周（{len(chapters)} 份教案）"
            )

    @staticmethod
    def _check_experiment_metadata(
        *,
        plan_date: Optional[str],
        first_class_date: Optional[str],
        class_periods: Optional[str],
        class_names: List[str],
        class_schedules: List[Dict[str, Any]],
    ) -> None:
        if not str(plan_date or "").strip():
            raise ValueError("生成实验计划时必须填写制表日期")
        scheduled = {
            str(item.get("class_name") or "").strip()
            for item in class_schedules
            if str(item.get("class_name") or "").strip()
        }
        missing = [name for name in class_names if name not in scheduled]
        if missing and (not str(first_class_date or "").strip() or not str(class_periods or "").strip()):
            raise ValueError(
                "班级 "
                + "、".join(missing)
                + " 缺少实验课安排，请填写其每周排课或补充首课日期与节次"
            )

    # ------------------------------------------------------------------- read

    async def get_course_plan(self, course_plan_id: str) -> Optional[CoursePlanDetail]:
        db = await get_db()
        row = await db.fetch_one(
            "SELECT * FROM course_plans WHERE id = ?",
            (course_plan_id,),
        )
        if not row:
            return None
        return self._row_to_detail(row)

    async def list_course_plans(
        self,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[CoursePlanListItem], int]:
        db = await get_db()
        where_clause = "WHERE status = ?" if status else ""
        params: List[Any] = [status] if status else []
        count_row = await db.fetch_one(
            f"SELECT COUNT(*) as count FROM course_plans {where_clause}",
            tuple(params),
        )
        total = count_row["count"] if count_row else 0
        offset = (page - 1) * limit
        rows = await db.fetch_all(
            f"""
            SELECT id, course_name, grade, teacher_name, class_names, plan_types,
                   status, created_at, updated_at
            FROM course_plans {where_clause}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        )
        items = [self._row_to_list_item(row) for row in rows]
        return items, total

    # ----------------------------------------------------------------- update

    async def update_course_plan(
        self,
        course_plan_id: str,
        request: CoursePlanUpdateRequest,
    ) -> CoursePlanDetail:
        db = await get_db()
        existing = await self.get_course_plan(course_plan_id)
        if not existing:
            raise ValueError(f"学期计划 {course_plan_id} 不存在")

        chapters = [chapter.model_dump() for chapter in request.chapters]
        self._check_capacity(chapters)
        # 用户编辑后的重难点若超限，保存原始内容并转入后台 AI 精简，
        # 避免同步等待超过站点代理的读超时。
        from .point_briefs import chapter_points_ok

        needs_condensing = any(not chapter_points_ok(c) for c in chapters)
        if "experiment_plan" in existing.plan_types:
            self._check_experiment_metadata(
                plan_date=request.plan_date,
                first_class_date=request.first_class_date,
                class_periods=request.class_periods,
                class_names=request.class_names,
                class_schedules=[
                    schedule.model_dump() for schedule in request.class_schedules
                ],
            )
            validate_experiment_chapters(chapters, require_every_group=True)

        await db.execute(
            """
            UPDATE course_plans SET
                course_name = ?, grade = ?, class_names = ?, academic_year = ?,
                semester = ?, teacher_name = ?, hours_per_lesson = ?,
                start_week = ?, total_hours = ?, location = ?, plan_date = ?,
                first_class_date = ?, class_periods = ?, class_schedules = ?,
                chapters = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                request.course_name.strip(),
                request.grade.strip(),
                ",".join(request.class_names),
                request.academic_year.strip(),
                request.semester,
                request.teacher_name.strip(),
                request.hours_per_lesson,
                request.start_week,
                request.total_hours,
                (request.location or "").strip(),
                (request.plan_date or "").strip(),
                (request.first_class_date or "").strip(),
                (request.class_periods or "").strip(),
                json.dumps(
                    [schedule.model_dump() for schedule in request.class_schedules],
                    ensure_ascii=False,
                ),
                json.dumps(chapters, ensure_ascii=False),
                datetime.now().isoformat(),
                course_plan_id,
            ),
            commit=True,
        )
        if needs_condensing:
            await db.execute(
                """
                UPDATE course_plans
                SET status = 'condensing', error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), course_plan_id),
                commit=True,
            )
            run_in_background(
                self._finalize_draft(course_plan_id),
                name=f"course-plan-condense-{course_plan_id[:8]}",
            )
        return await self.get_course_plan(course_plan_id)  # type: ignore[return-value]

    async def delete_course_plan(self, course_plan_id: str) -> None:
        db = await get_db()
        existing = await self.get_course_plan(course_plan_id)
        if not existing:
            raise ValueError(f"学期计划 {course_plan_id} 不存在")
        await db.execute(
            "DELETE FROM course_plans WHERE id = ?",
            (course_plan_id,),
            commit=True,
        )
        logger.info("Deleted course plan %s", course_plan_id)

    # ----------------------------------------------------------------- export

    async def export_course_plan(self, course_plan_id: str) -> Tuple[str, str]:
        """Render the plan into docx file(s); return (path, media_type)."""
        plan = await self.get_course_plan(course_plan_id)
        if not plan:
            raise ValueError(f"学期计划 {course_plan_id} 不存在")
        if plan.status == "condensing":
            raise ValueError("AI 正在精简重难点，请等待完成后再导出")
        from .point_briefs import chapter_points_ok

        if any(not chapter_points_ok(chapter.model_dump()) for chapter in plan.chapters):
            raise ValueError(
                "存在超限的重难点内容且未能自动精简"
                + (f"：{plan.error_message}" if plan.error_message else "")
                + "，请在编辑页修正后重试"
            )

        for plan_type in plan.plan_types:
            try:
                require_valid_course_plan_template(plan_type)
            except ValueError as exc:
                raise CoursePlanTemplateError(str(exc)) from exc

        chapters = [chapter.model_dump() for chapter in plan.chapters]
        self._check_capacity(chapters)
        class_names = plan.class_names
        if "experiment_plan" in plan.plan_types:
            self._check_experiment_metadata(
                plan_date=plan.plan_date,
                first_class_date=plan.first_class_date,
                class_periods=plan.class_periods,
                class_names=class_names,
                class_schedules=[
                    schedule.model_dump() for schedule in plan.class_schedules
                ],
            )
            validate_experiment_chapters(chapters, require_every_group=True)

        common = {
            "batch_task_id": course_plan_id,
            "course_name": plan.course_name,
            "grade": plan.grade,
            "class_names": class_names,
            "academic_year": plan.academic_year,
            "semester": plan.semester,
            "teacher_name": plan.teacher_name,
            "hours_per_lesson": plan.hours_per_lesson,
            "start_week": plan.start_week,
            "chapters": chapters,
            "location": plan.location,
        }

        files: List[str] = []
        if "teaching_plan" in plan.plan_types:
            files.append(
                self.course_plan_renderer.render_teaching_plan(
                    **common, total_hours=plan.total_hours
                )
            )
        if "experiment_plan" in plan.plan_types:
            files.extend(
                self.course_plan_renderer.render_experiment_plans(
                    **common,
                    plan_date=plan.plan_date,
                    first_class_date=plan.first_class_date,
                    class_periods=plan.class_periods,
                    class_schedules=[
                        schedule.model_dump() for schedule in plan.class_schedules
                    ],
                )
            )

        if not files:
            raise ValueError("学期计划未选择任何导出类型")

        output_path = files[0]
        media_type = DOCX_MEDIA_TYPE
        if len(files) > 1:
            zip_name = f"学期计划_{plan.course_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            safe_name = "".join(
                char if char not in '<>:"/\\|?*' else "_"
                for char in zip_name
            ).strip(" .")
            zip_path = settings.output_dir / safe_name
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for file_path in files:
                    archive.write(file_path, Path(file_path).name)
            output_path = str(zip_path)
            media_type = ZIP_MEDIA_TYPE

        db = await get_db()
        await db.execute(
            """
            UPDATE course_plans
            SET status = 'exported', output_files = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps([Path(path).name for path in files], ensure_ascii=False),
                datetime.now().isoformat(),
                course_plan_id,
            ),
            commit=True,
        )
        logger.info("Exported course plan %s to %s files", course_plan_id, len(files))
        return output_path, media_type

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _split_json(raw: Any, *, default: Any) -> Any:
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    @classmethod
    def _row_to_detail(cls, row: Any) -> CoursePlanDetail:
        return CoursePlanDetail(
            id=row["id"],
            course_name=row["course_name"],
            grade=row["grade"],
            class_names=[
                name.strip()
                for name in str(row["class_names"] or "").split(",")
                if name.strip()
            ],
            academic_year=row["academic_year"],
            semester=int(row["semester"] or 0),
            teacher_name=row["teacher_name"],
            hours_per_lesson=int(row["hours_per_lesson"] or 2),
            start_week=int(row["start_week"] or 1),
            total_hours=int(row["total_hours"] or 0),
            location=row["location"] or "",
            plan_date=row["plan_date"] or "",
            first_class_date=row["first_class_date"] or "",
            class_periods=row["class_periods"] or "",
            class_schedules=cls._split_json(row["class_schedules"], default=[]),
            plan_types=cls._split_json(row["plan_types"], default=[]),
            chapters=[
                CoursePlanChapter(**chapter)
                for chapter in cls._split_json(row["chapters"], default=[])
            ],
            source_lesson_plan_ids=cls._split_json(
                row["source_lesson_plan_ids"], default=[]
            ),
            status=row["status"],
            output_files=cls._split_json(row["output_files"], default=[]),
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_list_item(row: Any) -> CoursePlanListItem:
        return CoursePlanListItem(
            id=row["id"],
            course_name=row["course_name"],
            grade=row["grade"],
            teacher_name=row["teacher_name"],
            class_names=[
                name.strip()
                for name in str(row["class_names"] or "").split(",")
                if name.strip()
            ],
            plan_types=CoursePlanService._split_json(row["plan_types"], default=[]),
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


course_plan_service = CoursePlanService()
