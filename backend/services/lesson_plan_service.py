"""
Lesson Plan Service

Provides business logic for lesson plan management:
- CRUD operations for lesson plans
- Field-level updates and regeneration
- Publishing draft lesson plans to Word documents
- Batch operations (publish, delete, export)
"""
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4

from ..config import settings
from ..models.database import get_db
from ..models.schemas import (
    LessonPlan,
    LessonPlanInput,
    GeneratedContent,
)
from .ai_generator import AIGenerator
from .document_renderer import DocumentRenderer

logger = logging.getLogger(__name__)


class LessonPlanService:
    """Service for managing lesson plans."""

    def __init__(self):
        self.ai_generator = AIGenerator(
            provider=settings.ai_provider,
            api_key=settings.get_active_api_key(),
            model=settings.get_active_model(),
        )
        self.document_renderer = DocumentRenderer()

    async def get_lesson_plan(self, lesson_plan_id: str) -> Optional[LessonPlan]:
        """
        Get a lesson plan by ID.

        Args:
            lesson_plan_id: Lesson plan ID

        Returns:
            LessonPlan object or None if not found
        """
        db = await get_db()
        row = await db.fetch_one(
            "SELECT * FROM lesson_plans WHERE id = ?",
            (lesson_plan_id,)
        )

        if not row:
            return None

        return LessonPlan(**dict(row))

    async def list_lesson_plans(
        self,
        filters: Dict[str, Any],
        page: int,
        limit: int
    ) -> Tuple[List[LessonPlan], int]:
        """
        List lesson plans with optional filtering and pagination.

        Args:
            filters: Dictionary of filters (status, template_id, subject, grade, search)
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (lesson_plans list, total count)
        """
        db = await get_db()

        # Build WHERE clause
        where_clauses = []
        params = []

        if filters.get("status"):
            where_clauses.append("status = ?")
            params.append(filters["status"])

        if filters.get("template_id"):
            where_clauses.append("template_id = ?")
            params.append(filters["template_id"])

        if filters.get("subject"):
            where_clauses.append("subject = ?")
            params.append(filters["subject"])

        if filters.get("grade"):
            where_clauses.append("grade = ?")
            params.append(filters["grade"])

        if filters.get("search"):
            where_clauses.append("(title LIKE ? OR topic LIKE ?)")
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term])

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_sql = f"SELECT COUNT(*) as count FROM lesson_plans WHERE {where_clause}"
        count_row = await db.fetch_one(count_sql, tuple(params))
        total = count_row["count"] if count_row else 0

        # Get paginated results
        offset = (page - 1) * limit
        list_sql = f"""
            SELECT * FROM lesson_plans
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = await db.fetch_all(list_sql, tuple(params))

        lesson_plans = [LessonPlan(**dict(row)) for row in rows]

        return lesson_plans, total

    async def update_field(
        self,
        lesson_plan_id: str,
        field_name: str,
        field_value: Any
    ) -> LessonPlan:
        """
        Update a single field in a lesson plan's generated_content.

        Args:
            lesson_plan_id: Lesson plan ID
            field_name: Field name to update
            field_value: New value for the field

        Returns:
            Updated LessonPlan object
        """
        db = await get_db()

        # Get current lesson plan
        lesson_plan = await self.get_lesson_plan(lesson_plan_id)
        if not lesson_plan:
            raise ValueError(f"Lesson plan {lesson_plan_id} not found")

        # Parse generated_content
        try:
            content = json.loads(lesson_plan.generated_content) if lesson_plan.generated_content else {}
        except json.JSONDecodeError:
            content = {}

        # Update the field
        content[field_name] = field_value

        # Save back to database
        await db.execute(
            """
            UPDATE lesson_plans
            SET generated_content = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(content, ensure_ascii=False), datetime.now().isoformat(), lesson_plan_id),
            commit=True
        )

        # Return updated lesson plan
        return await self.get_lesson_plan(lesson_plan_id)

    async def regenerate_field(
        self,
        lesson_plan_id: str,
        field_name: str,
        additional_instruction: Optional[str] = None
    ) -> Any:
        """
        Regenerate a single field using AI.

        Args:
            lesson_plan_id: Lesson plan ID
            field_name: Field name to regenerate
            additional_instruction: Optional additional instructions for AI

        Returns:
            New field value
        """
        # Get lesson plan
        lesson_plan = await self.get_lesson_plan(lesson_plan_id)
        if not lesson_plan:
            raise ValueError(f"Lesson plan {lesson_plan_id} not found")

        # Parse input_data and generated_content
        try:
            input_data = json.loads(lesson_plan.input_data) if lesson_plan.input_data else {}
            content = json.loads(lesson_plan.generated_content) if lesson_plan.generated_content else {}
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in lesson plan data")

        # Convert input_data dict to LessonPlanInput object
        lesson_input = LessonPlanInput(**input_data)

        # Convert content dict to GeneratedContent object
        generated_content = GeneratedContent(**content)

        # Use AI generator to regenerate the field
        field_value = await self.ai_generator.regenerate_field(
            field_name=field_name,
            lesson_input=lesson_input,
            current_content=generated_content,
            additional_instruction=additional_instruction
        )

        # Update the field in database
        content[field_name] = field_value
        db = await get_db()
        await db.execute(
            """
            UPDATE lesson_plans
            SET generated_content = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(content, ensure_ascii=False), datetime.now().isoformat(), lesson_plan_id),
            commit=True
        )

        return field_value

    async def publish_lesson_plan(self, lesson_plan_id: str) -> Tuple[str, str]:
        """
        Publish a draft lesson plan by generating a Word document.

        Args:
            lesson_plan_id: Lesson plan ID

        Returns:
            Tuple of (output_file_path, download_url)
        """
        db = await get_db()

        # Get lesson plan
        lesson_plan = await self.get_lesson_plan(lesson_plan_id)
        if not lesson_plan:
            raise ValueError(f"Lesson plan {lesson_plan_id} not found")

        # Get template
        template_row = await db.fetch_one(
            "SELECT * FROM templates WHERE id = ?",
            (lesson_plan.template_id,)
        )
        if not template_row:
            raise ValueError(f"Template {lesson_plan.template_id} not found")

        template_path = template_row["file_path"]

        # Parse input_data and generated_content
        try:
            input_data = json.loads(lesson_plan.input_data) if lesson_plan.input_data else {}
            content_data = json.loads(lesson_plan.generated_content) if lesson_plan.generated_content else {}
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in lesson plan data")

        # Prepare data for template rendering
        template_data = {**input_data, **content_data}

        # Generate output filename
        safe_title = lesson_plan.topic or lesson_plan.title
        safe_title = "".join(c if c.isalnum() or c in "()[]_- " else "_" for c in safe_title)[:50]
        output_filename = f"{safe_title}_{lesson_plan_id[:8]}.docx"
        output_path = settings.output_dir / output_filename

        # Render document
        self.document_renderer.render(
            template_path=template_path,
            output_path=str(output_path),
            data=template_data
        )

        # Update lesson plan status and output_file_path
        await db.execute(
            """
            UPDATE lesson_plans
            SET status = 'published', output_file_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (str(output_path), datetime.now().isoformat(), lesson_plan_id),
            commit=True
        )

        # Generate download URL
        download_url = f"/api/documents/download/{output_filename}"

        logger.info(f"Published lesson plan {lesson_plan_id} to {output_filename}")

        return str(output_path), download_url

    async def batch_publish(
        self,
        lesson_plan_ids: List[str],
        group_by_document: bool = True
    ) -> str:
        """
        Batch publish multiple lesson plans and return a ZIP file.

        Args:
            lesson_plan_ids: List of lesson plan IDs to publish
            group_by_document: If True, group 2 lesson plans per document

        Returns:
            Path to the generated ZIP file
        """
        db = await get_db()

        # Load all lesson plans
        lesson_plans = []
        for plan_id in lesson_plan_ids:
            plan = await self.get_lesson_plan(plan_id)
            if plan:
                lesson_plans.append(plan)
            else:
                logger.warning(f"Lesson plan {plan_id} not found, skipping")

        if not lesson_plans:
            raise ValueError("No valid lesson plans found")

        # Group lesson plans by document
        if group_by_document:
            groups = [lesson_plans[i:i+2] for i in range(0, len(lesson_plans), 2)]
        else:
            groups = [[plan] for plan in lesson_plans]

        # Render documents
        doc_paths = []
        for idx, group in enumerate(groups, 1):
            try:
                doc_path = await self._render_combined_document(group, idx)
                doc_paths.append(doc_path)

                # Update lesson plans status
                for plan in group:
                    await db.execute(
                        """
                        UPDATE lesson_plans
                        SET status = 'published', output_file_path = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (doc_path, datetime.now().isoformat(), plan.id),
                        commit=True
                    )
            except Exception as e:
                logger.error(f"Failed to render document group {idx}: {str(e)}")
                # Continue with next group

        if not doc_paths:
            raise ValueError("Failed to generate any documents")

        # Create ZIP file
        zip_filename = f"lesson_plans_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = settings.output_dir / zip_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for doc_path in doc_paths:
                if Path(doc_path).exists():
                    zipf.write(doc_path, Path(doc_path).name)

        logger.info(f"Created ZIP file with {len(doc_paths)} documents: {zip_filename}")

        return str(zip_path)

    async def _render_combined_document(self, lesson_plans: List[LessonPlan], doc_number: int) -> str:
        """
        Render a combined document with multiple lesson plans.

        Args:
            lesson_plans: List of 1-2 lesson plans
            doc_number: Document number for filename

        Returns:
            Path to the generated document
        """
        if not lesson_plans:
            raise ValueError("No lesson plans provided")

        db = await get_db()

        # Use the first lesson plan's template
        first_plan = lesson_plans[0]
        template_row = await db.fetch_one(
            "SELECT * FROM templates WHERE id = ?",
            (first_plan.template_id,)
        )
        if not template_row:
            raise ValueError(f"Template {first_plan.template_id} not found")

        template_path = template_row["file_path"]

        # Prepare combined data
        # For 2 lesson plans per document, we need to combine their data
        combined_data = []
        for plan in lesson_plans:
            try:
                input_data = json.loads(plan.input_data) if plan.input_data else {}
                content_data = json.loads(plan.generated_content) if plan.generated_content else {}
                combined_data.append({**input_data, **content_data})
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in lesson plan {plan.id}")
                continue

        if not combined_data:
            raise ValueError("No valid lesson plan data")

        # For now, render the first lesson plan
        # TODO: Enhance document_renderer to support multiple lesson plans per document
        template_data = combined_data[0]

        # Generate output filename
        safe_title = lesson_plans[0].topic or lesson_plans[0].title
        safe_title = "".join(c if c.isalnum() or c in "()[]_- " else "_" for c in safe_title)[:50]
        output_filename = f"{safe_title}_{str(doc_number).zfill(2)}.docx"
        output_path = settings.output_dir / output_filename

        # Render document
        self.document_renderer.render(
            template_path=template_path,
            output_path=str(output_path),
            data=template_data
        )

        return str(output_path)

    async def delete_lesson_plan(self, lesson_plan_id: str) -> None:
        """
        Delete a lesson plan by ID.

        Args:
            lesson_plan_id: Lesson plan ID
        """
        db = await get_db()

        # Check if lesson plan exists
        lesson_plan = await self.get_lesson_plan(lesson_plan_id)
        if not lesson_plan:
            raise ValueError(f"Lesson plan {lesson_plan_id} not found")

        # Delete associated batch_lesson_plans records
        await db.execute(
            "DELETE FROM batch_lesson_plans WHERE lesson_plan_id = ?",
            (lesson_plan_id,),
            commit=True
        )

        # Delete the lesson plan
        await db.execute(
            "DELETE FROM lesson_plans WHERE id = ?",
            (lesson_plan_id,),
            commit=True
        )

        # Delete output file if exists
        if lesson_plan.output_file_path and Path(lesson_plan.output_file_path).exists():
            try:
                Path(lesson_plan.output_file_path).unlink()
                logger.info(f"Deleted output file: {lesson_plan.output_file_path}")
            except Exception as e:
                logger.error(f"Failed to delete output file: {str(e)}")

        logger.info(f"Deleted lesson plan {lesson_plan_id}")
