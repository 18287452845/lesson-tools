"""
Competition Renderer Service
============================

Renders Word documents for the competition module:
  1. Competition lesson plan (cover + overall design + N lessons)
  2. Implementation report

Templates live at storage/competition_templates/. Outputs go to storage/outputs/.

Lesson plan rendering strategy:
- Render `参赛教案_主模板.docx` once (cover + overall design)
- Render `参赛教案_单课模板.docx` once per lesson
- Merge all into a single output document

This sidesteps docxtpl's `{%p for %}` limitation (it can't loop content
that contains tables).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from docx import Document
from docxtpl import DocxTemplate

from ..config import settings
from ..models.schemas import (
    CompetitionProject,
    CompetitionLessonContent,
    CompetitionReportContent,
    CompetitionSingleLesson,
)
from .document_renderer import DocumentRenderer

logger = logging.getLogger(__name__)


COMPETITION_TEMPLATE_DIR = settings.storage_dir / "competition_templates"
LESSON_PLAN_MAIN_TEMPLATE = COMPETITION_TEMPLATE_DIR / "参赛教案_主模板.docx"
LESSON_PLAN_SINGLE_TEMPLATE = COMPETITION_TEMPLATE_DIR / "参赛教案_单课模板.docx"
REPORT_TEMPLATE = COMPETITION_TEMPLATE_DIR / "教学实施报告_模板.docx"


class CompetitionRenderer:
    """Render competition Word documents."""

    def __init__(self) -> None:
        self.output_dir = settings.output_dir
        self._base_renderer = DocumentRenderer()

    # ------------------------------------------------------------------
    # Lesson plan (multi-template merge)
    # ------------------------------------------------------------------

    def render_lesson_plan(
        self,
        project: CompetitionProject,
        content: CompetitionLessonContent,
    ) -> str:
        """
        Render a competition lesson plan by:
          1. Rendering main template (cover + overall design)
          2. Rendering single-lesson template once per lesson
          3. Merging all into one document
        """
        if not LESSON_PLAN_MAIN_TEMPLATE.exists():
            raise FileNotFoundError(
                f"Main template not found: {LESSON_PLAN_MAIN_TEMPLATE}. "
                "Run build_competition_templates.py to generate it."
            )
        if not LESSON_PLAN_SINGLE_TEMPLATE.exists():
            raise FileNotFoundError(
                f"Single-lesson template not found: {LESSON_PLAN_SINGLE_TEMPLATE}. "
                "Run build_competition_templates.py to generate it."
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_files: List[Path] = []

        try:
            # 1. Render main (cover + overall design)
            main_ctx = self._project_to_context(project)
            main_ctx["overall_design"] = self._clean_dict(
                content.overall_design.model_dump()
            )
            main_doc_path = self._render_to_temp(
                LESSON_PLAN_MAIN_TEMPLATE,
                main_ctx,
                temp_prefix="comp_main",
                timestamp=timestamp,
            )
            temp_files.append(main_doc_path)

            # 2. Render each lesson
            lesson_doc_paths: List[Path] = []
            for lesson in content.lessons:
                lesson_ctx = self._project_to_context(project)
                lesson_ctx["lesson"] = self._clean_dict(lesson.model_dump())
                lesson_doc_path = self._render_to_temp(
                    LESSON_PLAN_SINGLE_TEMPLATE,
                    lesson_ctx,
                    temp_prefix=f"comp_lesson_{lesson.lesson_number}",
                    timestamp=timestamp,
                )
                lesson_doc_paths.append(lesson_doc_path)
                temp_files.append(lesson_doc_path)

            # 3. Merge: main + all lessons
            output_path = self._merge_documents(
                base_path=main_doc_path,
                append_paths=lesson_doc_paths,
                output_filename=self._build_output_filename(
                    "参赛教案", project.work_name or "参赛作品", timestamp
                ),
            )
            return output_path

        finally:
            # Clean up temp files
            for f in temp_files:
                try:
                    f.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {f}: {e}")

    # ------------------------------------------------------------------
    # Implementation report (single template)
    # ------------------------------------------------------------------

    def render_report(
        self,
        project: CompetitionProject,
        content: CompetitionReportContent,
    ) -> str:
        if not REPORT_TEMPLATE.exists():
            raise FileNotFoundError(
                f"Report template not found: {REPORT_TEMPLATE}. "
                "Run build_competition_templates.py to generate it."
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ctx = self._project_to_context(project)
        ctx.update(self._clean_dict(content.model_dump()))

        tpl = DocxTemplate(str(REPORT_TEMPLATE))
        tpl.render(ctx)

        filename = self._build_output_filename(
            "教学实施报告", project.work_name or "参赛作品", timestamp
        )
        output_path = self.output_dir / filename
        tpl.save(str(output_path))
        logger.info(f"Report rendered: {output_path}")
        return str(output_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _render_to_temp(
        self,
        template_path: Path,
        context: Dict[str, Any],
        temp_prefix: str,
        timestamp: str,
    ) -> Path:
        """Render template to a temp file in output dir."""
        tpl = DocxTemplate(str(template_path))
        tpl.render(context)
        temp_path = self.output_dir / f"_temp_{temp_prefix}_{timestamp}.docx"
        tpl.save(str(temp_path))
        return temp_path

    def _merge_documents(
        self,
        base_path: Path,
        append_paths: List[Path],
        output_filename: str,
    ) -> str:
        """
        Merge multiple .docx files into one (continuous, no extra page breaks
        between body content - but we add a page break before each appended doc).
        """
        output_path = self.output_dir / output_filename
        combined = Document(str(base_path))

        for append_path in append_paths:
            sub = Document(str(append_path))
            # Add a page break before each appended lesson
            combined.add_page_break()
            for element in sub.element.body:
                if element.tag.endswith("sectPr"):
                    continue
                combined.element.body.append(element)

        combined.save(str(output_path))
        logger.info(f"Merged {1 + len(append_paths)} docs -> {output_path}")
        return str(output_path)

    @staticmethod
    def _build_output_filename(prefix: str, work_name: str, timestamp: str) -> str:
        safe_name = re.sub(r"[^\w一-鿿_.-]+", "_", work_name)[:60]
        return f"{prefix}_{safe_name}_{timestamp}.docx"

    @staticmethod
    def _project_to_context(project: CompetitionProject) -> Dict[str, Any]:
        return {
            "competition_year": project.competition_year or "",
            "competition_region": project.competition_region or "",
            "competition_level": project.competition_level or "",
            "work_name": project.work_name or "",
            "course_name": project.course_name or "",
            "major_category": project.major_category or "",
            "major_name": project.major_name or "",
            "group_name": project.group_name or "",
            "class_name": project.class_name or "",
            "location": project.location or "",
            "total_hours": project.total_hours,
            "hours_per_lesson": project.hours_per_lesson,
        }

    def _clean_dict(self, data: Any) -> Any:
        """Recursively clean text values: strip markdown, replace None with ''."""
        if data is None:
            return ""
        if isinstance(data, str):
            return self._base_renderer._clean_text_for_output(data)
        if isinstance(data, dict):
            return {k: self._clean_dict(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._clean_dict(item) for item in data]
        return data
