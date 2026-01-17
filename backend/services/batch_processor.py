"""
Batch task processor for generating multiple lesson plans.

Updated to support hours-based generation:
- Generate based on total hours (64, 72, etc.)
- Each lesson plan = 2 hours (configurable)
- 2 lesson plans per document
- File naming: course_name_01.docx, course_name_02.docx, etc.

Parallel processing:
- Document-level parallelization (configurable concurrency)
- Lesson-level parallelization within documents
- Connection pooling for efficient API calls
"""
import asyncio
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import uuid4

from ..config import settings
from ..models.database import get_db
from ..models.schemas import (
    LessonPlanInput,
    ChapterInfo,
    GeneratedContent,
)
from .ai_generator import AIGenerator
from .document_renderer import DocumentRenderer

logger = logging.getLogger(__name__)


class BatchTaskProcessor:
    """
    Process batch lesson plan generation tasks.

    Handles:
    - Loading batch tasks from database
    - Grouping lessons by document (2 lessons per document)
    - Generating lesson plans with sequential numbering
    - Rendering to Word documents
    - Updating progress in database
    - Packaging results into ZIP
    - Error handling and recovery
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        hours_per_lesson: int = 2,
        max_concurrent_documents: Optional[int] = None,
        max_concurrent_lessons: Optional[int] = None,
    ):
        """
        Initialize the batch processor.

        Args:
            provider: AI provider name
            api_key: API key for the provider
            model: Model name to use
            hours_per_lesson: Hours per lesson plan (default 2)
            max_concurrent_documents: Max concurrent document generation (uses config default if None)
            max_concurrent_lessons: Max concurrent lesson plan generation (uses config default if None)
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.hours_per_lesson = hours_per_lesson
        self.default_duration = f"{hours_per_lesson}课时"
        self.ai_generator = AIGenerator(provider, api_key, model)
        self.document_renderer = DocumentRenderer()

        # Concurrency settings (with config defaults)
        self.max_concurrent_documents = max_concurrent_documents or settings.batch_max_concurrent_documents
        self.max_concurrent_lessons = max_concurrent_lessons or settings.batch_max_concurrent_lessons

    async def process_batch_task(self, batch_task_id: str, is_draft_mode: bool = False) -> None:
        """
        Process a batch task - main entry point with parallel document generation.

        Args:
            batch_task_id: ID of the batch task to process
            is_draft_mode: If True, only generate content without rendering documents or creating ZIP

        This method runs the entire batch generation workflow with parallelization:
        1. Load task from database
        2. Group lessons by document (2 lessons per document)
        3. Generate documents concurrently (configurable concurrency)
        4. Generate lesson plans within each document concurrently
        5. Package all into ZIP (skipped in draft mode)
        6. Update task status
        """
        try:
            mode_str = "draft" if is_draft_mode else "normal"
            logger.info(
                f"Starting parallel batch task processing ({mode_str} mode): {batch_task_id} "
                f"(max_concurrent_documents={self.max_concurrent_documents}, "
                f"max_concurrent_lessons={self.max_concurrent_lessons})"
            )

            # Update status to processing
            await self._update_task_status(batch_task_id, "processing")

            # Load task details
            task = await self._load_batch_task(batch_task_id)
            if not task:
                raise ValueError(f"Batch task not found: {batch_task_id}")

            # Parse chapters
            chapters = json.loads(task["chapters"])

            # Group lessons by document (2 lessons per document)
            document_groups = self._group_lessons_by_document(chapters)

            # Track progress
            total_lesson_plans = len(chapters)
            completed_lesson_plans = 0
            progress_lock = asyncio.Lock()

            async def process_single_document(doc_number, doc_chapters):
                """
                Process a single document with parallel lesson generation.
                Returns (file_info, failed_count) tuple.
                """
                nonlocal completed_lesson_plans

                # Check if task was cancelled
                if await self._is_task_cancelled(batch_task_id):
                    logger.info(f"Batch task {batch_task_id} was cancelled by user")
                    return None, 0

                try:
                    logger.info(
                        f"Processing document {doc_number} with {len(doc_chapters)} lessons"
                    )

                    file_path = await self._generate_document_parallel(
                        batch_task_id=batch_task_id,
                        document_number=doc_number,
                        chapters_data=doc_chapters,
                        template_id=task["template_id"],
                        subject=task["subject"],
                        grade=task["grade"],
                        course_name=task["course_name"],
                        start_week=task.get("start_week", 1),
                        generate_reflection=task.get("generate_reflection", False),
                        location=task.get("location"),
                        textbook_name=task.get("textbook_name"),
                        online_resources=task.get("online_resources"),
                        class_names=task.get("class_names"),
                        is_draft_mode=is_draft_mode,
                    )

                    file_info = {
                        "doc_number": doc_number,
                        "topics": [c["topic"] for c in doc_chapters],
                        "file_path": file_path,
                    }

                    # Thread-safe progress update
                    async with progress_lock:
                        completed_lesson_plans += len(doc_chapters)
                        await self._update_task_progress(
                            batch_task_id,
                            completed=completed_lesson_plans,
                            total=total_lesson_plans,
                        )

                    return file_info, 0

                except Exception as e:
                    logger.error(
                        f"Failed to generate document {doc_number}: {str(e)}",
                        exc_info=True
                    )
                    # Return failed count for each lesson in this document
                    return None, len(doc_chapters)

            # Create semaphore for document-level concurrency
            doc_semaphore = asyncio.Semaphore(self.max_concurrent_documents)

            async def process_with_semaphore(doc_number, doc_chapters):
                async with doc_semaphore:
                    return await process_single_document(doc_number, doc_chapters)

            # Process all documents concurrently
            tasks = [
                process_with_semaphore(doc_number, doc_chapters)
                for doc_number, doc_chapters in enumerate(document_groups, start=1)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            generated_files = []
            failed_lessons = 0

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Unexpected error in document task: {result}")
                    failed_lessons += 1
                elif result is not None:
                    file_info, failed_count = result
                    if file_info:
                        generated_files.append(file_info)
                    failed_lessons += failed_count

            # Update failed count in database
            for _ in range(failed_lessons):
                await self._increment_failed_count(batch_task_id)

            # Check if cancelled during processing
            if await self._is_task_cancelled(batch_task_id):
                await self._update_task_status(batch_task_id, "cancelled")
                return

            # Package all files into ZIP (skip in draft mode)
            if is_draft_mode:
                # In draft mode, no files are generated, so just mark as completed
                await self._update_task_status(
                    batch_task_id,
                    "completed",
                    completed_at=datetime.now().isoformat(),
                )

                logger.info(
                    f"Draft batch task {batch_task_id} completed successfully. "
                    f"Generated {completed_lesson_plans} lesson plans ({failed_lessons} failed). "
                    f"All lesson plans saved as drafts (no documents rendered)."
                )
            elif generated_files:
                zip_path = await self._pack_zip(
                    batch_task_id=batch_task_id,
                    course_name=task["course_name"],
                    files=generated_files,
                )

                # Update task with ZIP path and mark as completed
                await self._update_task_status(
                    batch_task_id,
                    "completed",
                    zip_file_path=zip_path,
                    completed_at=datetime.now().isoformat(),
                )

                logger.info(
                    f"Batch task {batch_task_id} completed successfully. "
                    f"Generated {len(generated_files)} documents ({failed_lessons} failed)."
                )
            else:
                # No files generated - all failed
                await self._update_task_status(
                    batch_task_id,
                    "failed",
                    error_message="All lesson plan generations failed",
                )
                logger.error(f"Batch task {batch_task_id} failed: No files generated")

        except Exception as e:
            logger.error(
                f"Batch task {batch_task_id} processing failed: {str(e)}",
                exc_info=True
            )
            await self._update_task_status(
                batch_task_id,
                "failed",
                error_message=str(e),
            )

    def _group_lessons_by_document(
        self,
        chapters: List[Dict],
        lessons_per_doc: int = 2
    ) -> List[List[Dict]]:
        """
        Group lessons into documents (default 2 lessons per document).

        Args:
            chapters: List of chapter data dictionaries
            lessons_per_doc: Number of lesson plans per document (default 2)

        Returns:
            List of chapter groups, each group becomes one document
        """
        groups = []
        for i in range(0, len(chapters), lessons_per_doc):
            groups.append(chapters[i:i + lessons_per_doc])
        return groups

    async def _generate_document_parallel(
        self,
        batch_task_id: str,
        document_number: int,
        chapters_data: List[Dict],
        template_id: str,
        subject: str,
        grade: str,
        course_name: str,
        start_week: int = 1,
        generate_reflection: bool = False,
        location: Optional[str] = None,
        textbook_name: Optional[str] = None,
        online_resources: Optional[str] = None,
        class_names: Optional[str] = None,
        is_draft_mode: bool = False,
    ) -> str:
        """
        Generate a document containing lesson plans with parallel lesson generation.

        This method generates all lesson plans for a document concurrently,
        then renders them together. Failed individual lessons don't fail the entire document.

        Args:
            batch_task_id: ID of the batch task
            document_number: Document sequence number (1, 2, 3...)
            chapters_data: List of chapter data for this document (usually 2)
            template_id: Template to use
            subject: Subject area
            grade: Grade level
            course_name: Course name for file naming
            start_week: Starting week number (default 1)
            generate_reflection: Whether to generate teaching reflection (default False)
            location: Optional location context
            textbook_name: Optional textbook name
            online_resources: Optional online resources
            class_names: Optional class names (comma-separated)
            is_draft_mode: If True, only save content without rendering document (default False)

        Returns:
            Path to the generated .docx file (or empty string in draft mode)
        """
        # Calculate week number (each document = 1 week)
        week_number = start_week + (document_number - 1)

        # Get template file path from database
        db = await get_db()
        template_row = await db.fetch_one(
            "SELECT file_path FROM templates WHERE id = ?",
            (template_id,)
        )
        if not template_row:
            raise ValueError(f"Template not found: {template_id}")

        template_path = template_row["file_path"]

        # Create semaphore for lesson-level concurrency
        lesson_semaphore = asyncio.Semaphore(self.max_concurrent_lessons)

        async def generate_single_lesson_plan(chapter_data):
            """Generate a single lesson plan with concurrency control."""
            async with lesson_semaphore:
                chapter = ChapterInfo(**chapter_data)

                # Create lesson plan input
                lesson_input = LessonPlanInput(
                    template_id=template_id,
                    subject=subject,
                    grade=grade,
                    topic=chapter.topic,
                    duration=self.default_duration,
                    prior_knowledge=chapter.content_summary,
                    focus_areas=", ".join(chapter.key_concepts),
                    location=location,
                    textbook_name=textbook_name,
                    online_resources=online_resources,
                    class_name=class_names,
                )

                # Generate content using AI
                logger.debug(f"Generating AI content for: {chapter.topic}")
                generated_content = await self.ai_generator.generate_lesson_plan(
                    lesson_input,
                    generate_reflection=generate_reflection
                )

                # Prepare lesson plan data for rendering
                # Build references from textbook_name and online_resources
                online_res = online_resources or generated_content.online_resources or ""
                references_parts = []
                if textbook_name:
                    # Add book title marks around textbook name
                    references_parts.append(f"《{textbook_name}》")
                if online_res:
                    references_parts.append(online_res)
                references = "\n".join(references_parts) if references_parts else ""

                lesson_plan_data = {
                    **lesson_input.model_dump(),
                    **generated_content.model_dump(),
                    "lesson_number": chapter.lesson_number,
                    "week_number": week_number,
                    "week_display": f"第{week_number}周",
                    "references": references,  # Add built references
                    "online_resources": online_res,  # Use final online_resources
                }

                return chapter, lesson_plan_data, generated_content

        # Generate all lesson plans concurrently
        lesson_tasks = [
            generate_single_lesson_plan(chapter_data)
            for chapter_data in chapters_data
        ]

        lesson_results = await asyncio.gather(*lesson_tasks, return_exceptions=True)

        # Process results and create database records
        lesson_plans_data = []

        for result in lesson_results:
            if isinstance(result, Exception):
                logger.error(f"Lesson generation failed: {result}", exc_info=True)
                # Increment failed count for this lesson
                await self._increment_failed_count(batch_task_id)
                # Continue with next lesson (don't fail entire document)
                continue

            chapter, lesson_plan_data, generated_content = result

            # Create lesson plan record in database
            lesson_plan_id = str(uuid4())
            # Set status based on draft mode
            lesson_plan_status = "draft_cached" if is_draft_mode else "generated"

            await db.execute(
                """
                INSERT INTO lesson_plans (
                    id, template_id, title, subject, grade, topic,
                    input_data, generated_content, status,
                    batch_task_id, lesson_number, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lesson_plan_id,
                    template_id,
                    f"教案{chapter.lesson_number}：{chapter.topic}",
                    subject,
                    grade,
                    chapter.topic,
                    json.dumps(LessonPlanInput(
                        template_id=template_id,
                        subject=subject,
                        grade=grade,
                        topic=chapter.topic,
                        duration=self.default_duration,
                        prior_knowledge=chapter.content_summary,
                        focus_areas=", ".join(chapter.key_concepts),
                    ).model_dump(), ensure_ascii=False),
                    json.dumps(generated_content.model_dump(), ensure_ascii=False),
                    lesson_plan_status,
                    batch_task_id,
                    chapter.lesson_number,
                    datetime.now().isoformat(),
                ),
                commit=True,
            )

            # Create batch_lesson_plans record
            batch_lesson_plan_id = str(uuid4())
            await db.execute(
                """
                INSERT INTO batch_lesson_plans (
                    id, batch_task_id, lesson_plan_id, lesson_number,
                    topic, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_lesson_plan_id,
                    batch_task_id,
                    lesson_plan_id,
                    chapter.lesson_number,
                    chapter.topic,
                    "completed",
                    datetime.now().isoformat(),
                ),
                commit=True,
            )

            # Validate lesson plan data completeness before appending
            required_fields = ["teaching_goals", "key_points", "teaching_steps"]
            missing_fields = [
                f for f in required_fields
                if f not in lesson_plan_data or not lesson_plan_data[f]
            ]
            if missing_fields:
                logger.error(
                    f"Lesson plan {chapter.lesson_number} ({chapter.topic}) "
                    f"is missing required fields: {missing_fields}. "
                    f"Skipping this lesson plan."
                )
                await self._increment_failed_count(batch_task_id)
                continue

            lesson_plans_data.append(lesson_plan_data)

        # Check if we have any successful lesson plans
        if not lesson_plans_data:
            raise ValueError(f"All lesson plans failed for document {document_number}")

        # In draft mode, skip document rendering and return empty string
        if is_draft_mode:
            logger.info(
                f"Draft mode: Skipping document rendering for document {document_number}. "
                f"Generated {len(lesson_plans_data)} lesson plans."
            )
            return ""

        # Render combined document with successful lesson plans
        logger.debug(f"Rendering document {document_number} (week {week_number}) with {len(lesson_plans_data)} lesson plans")
        output_path = self.document_renderer.render_lesson_plans_document(
            template_path=template_path,
            lesson_plans_data=lesson_plans_data,
            course_name=course_name,
            document_number=document_number,
            week_number=week_number,
        )

        # Update file path in batch_lesson_plans records for successful lessons
        lesson_numbers = [
            chapter_data["lesson_number"]
            for chapter_data in chapters_data
        ]
        placeholders = ",".join(["?"] * len(lesson_numbers))
        await db.execute(
            f"""
            UPDATE batch_lesson_plans
            SET file_path = ?
            WHERE batch_task_id = ? AND lesson_number IN ({placeholders})
            """,
            (output_path, batch_task_id, *lesson_numbers),
            commit=True,
        )

        logger.info(f"Successfully generated document {document_number}: {output_path}")
        return output_path

    async def _generate_document_sequential(
        self,
        batch_task_id: str,
        document_number: int,
        chapters_data: List[Dict],
        template_id: str,
        subject: str,
        grade: str,
        course_name: str,
        start_week: int = 1,
        generate_reflection: bool = False,
        location: Optional[str] = None,
        textbook_name: Optional[str] = None,
        online_resources: Optional[str] = None,
    ) -> str:
        """
        Generate a document containing lesson plans (sequential version for fallback).

        Args:
            batch_task_id: ID of the batch task
            document_number: Document sequence number (1, 2, 3...)
            chapters_data: List of chapter data for this document (usually 2)
            template_id: Template to use
            subject: Subject area
            grade: Grade level
            course_name: Course name for file naming
            start_week: Starting week number (default 1)
            generate_reflection: Whether to generate teaching reflection (default False)

        Returns:
            Path to the generated .docx file
        """
        # Calculate week number (each document = 1 week)
        week_number = start_week + (document_number - 1)
        # Get template file path from database
        db = await get_db()
        template_row = await db.fetch_one(
            "SELECT file_path FROM templates WHERE id = ?",
            (template_id,)
        )
        if not template_row:
            raise ValueError(f"Template not found: {template_id}")

        template_path = template_row["file_path"]

        # Generate content for each chapter
        lesson_plans_data = []
        for chapter_data in chapters_data:
            chapter = ChapterInfo(**chapter_data)

            # Create lesson plan input
            lesson_input = LessonPlanInput(
                template_id=template_id,
                subject=subject,
                grade=grade,
                topic=chapter.topic,
                duration=self.default_duration,
                prior_knowledge=chapter.content_summary,
                focus_areas=", ".join(chapter.key_concepts),
                location=location,
                textbook_name=textbook_name,
                online_resources=online_resources,
            )

            # Generate content using AI
            logger.debug(f"Generating AI content for: {chapter.topic}")
            generated_content = await self.ai_generator.generate_lesson_plan(
                lesson_input,
                generate_reflection=generate_reflection
            )

            # Create lesson plan record in database
            lesson_plan_id = str(uuid4())
            await db.execute(
                """
                INSERT INTO lesson_plans (
                    id, template_id, title, subject, grade, topic,
                    input_data, generated_content, status,
                    batch_task_id, lesson_number, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lesson_plan_id,
                    template_id,
                    f"教案{chapter.lesson_number}：{chapter.topic}",
                    subject,
                    grade,
                    chapter.topic,
                    json.dumps(lesson_input.model_dump(), ensure_ascii=False),
                    json.dumps(generated_content.model_dump(), ensure_ascii=False),
                    "generated",
                    batch_task_id,
                    chapter.lesson_number,
                    datetime.now().isoformat(),
                ),
                commit=True,
            )

            # Prepare lesson plan data for rendering
            lesson_plan_data = {
                **lesson_input.model_dump(),
                **generated_content.model_dump(),
                "lesson_number": chapter.lesson_number,
                "week_number": week_number,
                "week_display": f"第{week_number}周",
            }
            lesson_plans_data.append(lesson_plan_data)

            # Create batch_lesson_plans record
            batch_lesson_plan_id = str(uuid4())
            await db.execute(
                """
                INSERT INTO batch_lesson_plans (
                    id, batch_task_id, lesson_plan_id, lesson_number,
                    topic, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_lesson_plan_id,
                    batch_task_id,
                    lesson_plan_id,
                    chapter.lesson_number,
                    chapter.topic,
                    "completed",
                    datetime.now().isoformat(),
                ),
                commit=True,
            )

        # Render combined document with all lesson plans
        logger.debug(f"Rendering document {document_number} (week {week_number})")
        output_path = self.document_renderer.render_lesson_plans_document(
            template_path=template_path,
            lesson_plans_data=lesson_plans_data,
            course_name=course_name,
            document_number=document_number,
            week_number=week_number,
        )

        # Update file path in batch_lesson_plans records
        lesson_numbers = [c["lesson_number"] for c in chapters_data]
        placeholders = ",".join(["?"] * len(lesson_numbers))
        await db.execute(
            f"""
            UPDATE batch_lesson_plans
            SET file_path = ?
            WHERE batch_task_id = ? AND lesson_number IN ({placeholders})
            """,
            (output_path, batch_task_id, *lesson_numbers),
            commit=True,
        )

        logger.info(f"Successfully generated document {document_number}: {output_path}")
        return output_path

    async def _pack_zip(
        self,
        batch_task_id: str,
        course_name: str,
        files: List[Dict[str, Any]],
    ) -> str:
        """
        Package all generated files into a ZIP archive.

        Args:
            batch_task_id: Batch task ID
            course_name: Name of the course
            files: List of file info dicts with 'week', 'topic', 'file_path'

        Returns:
            Path to the generated ZIP file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{course_name}_批量教案_{timestamp}.zip"
        zip_path = Path(settings.output_dir) / zip_filename

        logger.info(f"Creating ZIP archive: {zip_path}")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_info in files:
                file_path = Path(file_info["file_path"])
                if file_path.exists():
                    # Use the original filename which already has the format
                    arcname = file_path.name
                    zipf.write(file_path, arcname=arcname)
                    logger.debug(f"Added to ZIP: {arcname}")
                else:
                    logger.warning(f"File not found, skipping: {file_path}")

        logger.info(
            f"ZIP archive created successfully: {zip_path} "
            f"({len(files)} files)"
        )

        return str(zip_path)

    async def _load_batch_task(self, batch_task_id: str) -> Optional[Dict]:
        """Load batch task from database."""
        db = await get_db()
        row = await db.fetch_one(
            "SELECT * FROM batch_tasks WHERE id = ?",
            (batch_task_id,)
        )
        return dict(row) if row else None

    async def _update_task_status(
        self,
        batch_task_id: str,
        status: str,
        **extra_fields,
    ) -> None:
        """
        Update batch task status and other fields.

        Args:
            batch_task_id: Batch task ID
            status: New status
            **extra_fields: Additional fields to update (zip_file_path, error_message, etc.)
        """
        db = await get_db()

        # Build UPDATE query dynamically
        update_fields = ["status = ?", "updated_at = ?"]
        params = [status, datetime.now().isoformat()]

        for key, value in extra_fields.items():
            update_fields.append(f"{key} = ?")
            params.append(value)

        params.append(batch_task_id)

        sql = f"""
            UPDATE batch_tasks
            SET {', '.join(update_fields)}
            WHERE id = ?
        """

        await db.execute(sql, tuple(params), commit=True)
        logger.debug(f"Updated batch task {batch_task_id}: status={status}")

    async def _update_task_progress(
        self,
        batch_task_id: str,
        completed: int,
        total: int,
    ) -> None:
        """
        Update task progress counters.

        Args:
            batch_task_id: Batch task ID
            completed: Number of completed lesson plans
            total: Total number of lesson plans
        """
        db = await get_db()
        await db.execute(
            """
            UPDATE batch_tasks
            SET completed_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (completed, datetime.now().isoformat(), batch_task_id),
            commit=True,
        )
        logger.debug(
            f"Updated progress for {batch_task_id}: {completed}/{total}"
        )

    async def _increment_failed_count(self, batch_task_id: str) -> None:
        """Increment the failed lesson plans counter."""
        db = await get_db()
        await db.execute(
            """
            UPDATE batch_tasks
            SET failed_count = failed_count + 1, updated_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), batch_task_id),
            commit=True,
        )
        logger.debug(f"Incremented failed count for {batch_task_id}")

    async def _is_task_cancelled(self, batch_task_id: str) -> bool:
        """Check if the task has been cancelled by user."""
        db = await get_db()
        row = await db.fetch_one(
            "SELECT status FROM batch_tasks WHERE id = ?",
            (batch_task_id,)
        )
        return row is not None and row["status"] == "cancelled"


async def process_batch_task(
    batch_task_id: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    """
    Convenience function to process a batch task.

    Args:
        batch_task_id: ID of the batch task
        provider: AI provider name
        api_key: Optional API key
        model: Optional model name
    """
    processor = BatchTaskProcessor(provider, api_key, model)
    await processor.process_batch_task(batch_task_id)
