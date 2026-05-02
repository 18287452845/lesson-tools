"""
Competition Renderer Service
============================

Renders Word documents for the competition module:
  1. Competition lesson plan (from CompetitionLessonContent + CompetitionProject)
  2. Implementation report (from CompetitionReportContent + CompetitionProject)

Templates live at storage/competition_templates/. Outputs go to storage/outputs/.

Key design:
- Inherits markdown-cleaning logic from DocumentRenderer
- Uses docxtpl for proper Jinja2 template rendering
- Recursive cleaning of nested dict/list structures before render
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from docxtpl import DocxTemplate

from ..config import settings
from ..models.schemas import (
    CompetitionProject,
    CompetitionLessonContent,
    CompetitionReportContent,
)
from .document_renderer import DocumentRenderer

logger = logging.getLogger(__name__)


COMPETITION_TEMPLATE_DIR = settings.template_dir.parent / "competition_templates"
LESSON_PLAN_TEMPLATE = COMPETITION_TEMPLATE_DIR / "参赛教案_模板.docx"
REPORT_TEMPLATE = COMPETITION_TEMPLATE_DIR / "教学实施报告_模板.docx"


class CompetitionRenderer:
    """Render competition Word documents."""

    def __init__(self) -> None:
        self.output_dir = settings.output_dir
        # Reuse markdown cleaner from DocumentRenderer
        self._base_renderer = DocumentRenderer()

    # ------------------------------------------------------------------
    # Public render methods
    # ------------------------------------------------------------------

    def render_lesson_plan(
        self,
        project: CompetitionProject,
        content: CompetitionLessonContent,
    ) -> str:
        """Render a competition lesson plan to Word."""
        if not LESSON_PLAN_TEMPLATE.exists():
            raise FileNotFoundError(
                f"Lesson plan template not found: {LESSON_PLAN_TEMPLATE}. "
                "Run build_competition_templates.py to generate it."
            )

        data = self._build_lesson_plan_context(project, content)
        return self._render(LESSON_PLAN_TEMPLATE, data, prefix="参赛教案")

    def render_report(
        self,
        project: CompetitionProject,
        content: CompetitionReportContent,
    ) -> str:
        """Render a teaching implementation report to Word."""
        if not REPORT_TEMPLATE.exists():
            raise FileNotFoundError(
                f"Report template not found: {REPORT_TEMPLATE}. "
                "Run build_competition_templates.py to generate it."
            )

        data = self._build_report_context(project, content)
        return self._render(REPORT_TEMPLATE, data, prefix="教学实施报告")

    # ------------------------------------------------------------------
    # Context builders
    # ------------------------------------------------------------------

    def _build_lesson_plan_context(
        self,
        project: CompetitionProject,
        content: CompetitionLessonContent,
    ) -> Dict[str, Any]:
        """Build the Jinja2 context for the lesson plan template."""
        ctx = self._project_to_context(project)
        ctx["overall_design"] = self._clean_dict(
            content.overall_design.model_dump()
        )
        ctx["lessons"] = [
            self._clean_dict(lesson.model_dump()) for lesson in content.lessons
        ]
        return ctx

    def _build_report_context(
        self,
        project: CompetitionProject,
        content: CompetitionReportContent,
    ) -> Dict[str, Any]:
        """Build the Jinja2 context for the report template."""
        ctx = self._project_to_context(project)
        ctx.update(self._clean_dict(content.model_dump()))
        return ctx

    @staticmethod
    def _project_to_context(project: CompetitionProject) -> Dict[str, Any]:
        """Map CompetitionProject fields into template variables."""
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

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Render & save
    # ------------------------------------------------------------------

    def _render(self, template_path: Path, context: Dict[str, Any], prefix: str) -> str:
        """Render template with context and save to output dir."""
        logger.info(f"Rendering competition template: {template_path.name}")

        tpl = DocxTemplate(str(template_path))
        tpl.render(context)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize project / work name for filename
        work_name = context.get("work_name") or "竞赛作品"
        safe_name = re.sub(r"[^\w一-鿿_.-]+", "_", work_name)[:60]
        filename = f"{prefix}_{safe_name}_{timestamp}.docx"
        output_path = self.output_dir / filename

        tpl.save(str(output_path))
        logger.info(f"Competition document saved: {output_path}")
        return str(output_path)
