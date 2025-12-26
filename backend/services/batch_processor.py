"""
Batch task processor for generating multiple lesson plans.
"""
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
    - Generating lesson plans sequentially
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
    ):
        """
        Initialize the batch processor.

        Args:
            provider: AI provider name
            api_key: API key for the provider
            model: Model name to use
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.ai_generator = AIGenerator(provider, api_key, model)
        self.document_renderer = DocumentRenderer()

    async def process_batch_task(self, batch_task_id: str) -> None:
        """
        Process a batch task - main entry point.

        Args:
            batch_task_id: ID of the batch task to process

        This method runs the entire batch generation workflow:
        1. Load task from database
        2. Generate each lesson plan sequentially
        3. Package all into ZIP
        4. Update task status
        """
        try:
            logger.info(f"Starting batch task processing: {batch_task_id}")

            # Update status to processing
            await self._update_task_status(batch_task_id, "processing")

            # Load task details
            task = await self._load_batch_task(batch_task_id)
            if not task:
                raise ValueError(f"Batch task not found: {batch_task_id}")

            # Parse chapters
            chapters = json.loads(task["chapters"])

            # Generate each lesson plan
            generated_files = []
            for idx, chapter_data in enumerate(chapters):
                try:
                    chapter = ChapterInfo(**chapter_data)
                    logger.info(
                        f"Processing chapter {idx + 1}/{len(chapters)}: "
                        f"Week {chapter.week} - {chapter.topic}"
                    )

                    file_path = await self._generate_single_lesson(
                        batch_task_id=batch_task_id,
                        chapter=chapter,
                        template_id=task["template_id"],
                        subject=task["subject"],
                        grade=task["grade"],
                    )

                    generated_files.append({
                        "week": chapter.week,
                        "topic": chapter.topic,
                        "file_path": file_path,
                    })

                    # Update progress
                    await self._update_task_progress(
                        batch_task_id,
                        completed=idx + 1,
                        total=len(chapters),
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to generate lesson for week {chapter.week}: {str(e)}",
                        exc_info=True
                    )
                    # Update failed count
                    await self._increment_failed_count(batch_task_id)

                    # Continue with next chapter (don't abort entire batch)
                    continue

            # Package all files into ZIP
            if generated_files:
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
                    f"Generated {len(generated_files)} lesson plans."
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

    async def _generate_single_lesson(
        self,
        batch_task_id: str,
        chapter: ChapterInfo,
        template_id: str,
        subject: str,
        grade: str,
    ) -> str:
        """
        Generate a single lesson plan.

        Args:
            batch_task_id: ID of the batch task
            chapter: Chapter information
            template_id: Template to use
            subject: Subject area
            grade: Grade level

        Returns:
            Path to the generated .docx file
        """
        # Create lesson plan input
        lesson_input = LessonPlanInput(
            template_id=template_id,
            subject=subject,
            grade=grade,
            topic=chapter.topic,
            duration="2课时",  # Fixed at 2 class hours
            prior_knowledge=chapter.content_summary,
            focus_areas=", ".join(chapter.key_concepts),
        )

        # Generate content using AI
        logger.debug(f"Generating AI content for: {chapter.topic}")
        generated_content = await self.ai_generator.generate_lesson_plan(lesson_input)

        # Create lesson plan record in database
        lesson_plan_id = str(uuid4())
        db = await get_db()

        await db.execute(
            """
            INSERT INTO lesson_plans (
                id, template_id, title, subject, grade, topic,
                input_data, generated_content, status,
                batch_task_id, week_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson_plan_id,
                template_id,
                f"第{chapter.week:02d}周 - {chapter.topic}",
                subject,
                grade,
                chapter.topic,
                json.dumps(lesson_input.model_dump(), ensure_ascii=False),
                json.dumps(generated_content.model_dump(), ensure_ascii=False),
                "generated",
                batch_task_id,
                chapter.week,
                datetime.now().isoformat(),
            ),
            commit=True,
        )

        # Get template file path from database
        template_row = await db.fetch_one(
            "SELECT file_path FROM templates WHERE id = ?",
            (template_id,)
        )
        if not template_row:
            raise ValueError(f"Template not found: {template_id}")

        template_path = template_row["file_path"]

        # Render to Word document
        logger.debug(f"Rendering document for: {chapter.topic}")

        # Prepare lesson plan data for rendering
        lesson_plan_data = {
            **lesson_input.model_dump(),
            **generated_content.model_dump(),
            "week_number": chapter.week,
        }

        output_path = self.document_renderer.render_lesson_plan(
            template_path=template_path,
            lesson_plan_data=lesson_plan_data,
        )

        # Update lesson plan with output file path
        await db.execute(
            """
            UPDATE lesson_plans
            SET output_file_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (output_path, datetime.now().isoformat(), lesson_plan_id),
            commit=True,
        )

        # Create batch_lesson_plans record
        batch_lesson_plan_id = str(uuid4())
        await db.execute(
            """
            INSERT INTO batch_lesson_plans (
                id, batch_task_id, lesson_plan_id, week_number,
                topic, status, file_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_lesson_plan_id,
                batch_task_id,
                lesson_plan_id,
                chapter.week,
                chapter.topic,
                "completed",
                output_path,
                datetime.now().isoformat(),
            ),
            commit=True,
        )

        logger.info(f"Successfully generated lesson plan: {output_path}")
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
