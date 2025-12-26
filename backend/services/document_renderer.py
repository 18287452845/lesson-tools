"""
Document renderer service for generating lesson plans from templates.

Uses docxtpl (not python-docx) for template rendering to preserve document structure.
See WORD_EXPORT_FIX.md for details.
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from docxtpl import DocxTemplate

from ..config import settings

logger = logging.getLogger(__name__)


class DocumentRenderer:
    """
    Render Word documents from templates using docxtpl.

    This approach properly renders Jinja2 templates while preserving
    the original document structure, including tables and formatting.
    """

    def __init__(self):
        """Initialize the document renderer."""
        self.template_dir = settings.template_dir
        self.output_dir = settings.output_dir

    def render_lesson_plan(
        self,
        template_path: str,
        lesson_plan_data: Dict[str, Any],
    ) -> str:
        """
        Render a complete lesson plan using docxtpl.

        Args:
            template_path: Path to the template file
            lesson_plan_data: Complete lesson plan data with all sections

        Returns:
            Path to the generated document
        """
        # Process data for rendering
        processed_data = self._process_data(lesson_plan_data)

        # Debug: Check for None values in iterable fields
        iterable_fields = []
        for key, value in processed_data.items():
            if value is None:
                logger.warning(f"Field '{key}' is None - setting to empty list/string")
                processed_data[key] = []
            elif isinstance(value, dict):
                # Check nested dict values
                for sub_key, sub_value in value.items():
                    if sub_value is None:
                        logger.warning(f"Nested field '{key}.{sub_key}' is None - setting to empty list")
                        value[sub_key] = []

        # Load template using docxtpl
        template = DocxTemplate(template_path)

        # Render with Jinja2
        template.render(processed_data)

        # Generate output path
        topic = lesson_plan_data.get("topic", "教案")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{topic}_{timestamp}.docx"
        output_path = str(self.output_dir / output_filename)

        # Save the rendered document
        template.save(output_path)

        return output_path

    def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data for template filling.

        Converts complex data structures into formats suitable for Jinja2 rendering.
        """
        processed = {}

        # Copy all simple fields
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                processed[key] = value if value is not None else ""

        # Process teaching_goals
        if "teaching_goals" in data:
            goals = data["teaching_goals"]
            if isinstance(goals, dict):
                # Handle structured goals
                processed["teaching_goals"] = goals

                # Also provide flat access - convert None to empty string or list
                processed["knowledge"] = goals.get("knowledge") or []
                processed["ability"] = goals.get("ability") or []
                processed["emotion"] = goals.get("emotion") or []
                processed["quality"] = goals.get("quality") or []

                # Legacy field names for compatibility
                processed["knowledge_objectives"] = goals.get("knowledge") or []
                processed["ability_objectives"] = goals.get("ability") or []
                processed["quality_objectives"] = goals.get("emotion") or goals.get("quality") or []
            elif isinstance(goals, str):
                processed["teaching_goals"] = goals
            else:
                processed["teaching_goals"] = ""

        # Process teaching_steps - keep as list for Jinja2 {% for %} loops
        if "teaching_steps" in data:
            steps = data["teaching_steps"]
            if isinstance(steps, list):
                processed["teaching_steps"] = steps

                # Also create combined text versions for templates without loops
                step_texts = []
                for i, step in enumerate(steps):
                    if isinstance(step, dict):
                        stage = step.get("stage", "") or step.get("title", "")
                        duration = step.get("duration", "")
                        teacher = step.get("teacher_activity", "")
                        student = step.get("student_activity", "")
                        intent = step.get("design_intent", "")
                        content = step.get("content", "")

                        parts = []
                        if stage:
                            parts.append(f"【{stage}】")
                        if duration:
                            parts.append(f"（{duration}）")
                        if content:
                            parts.append(content)
                        if teacher:
                            parts.append(f"教师活动：{teacher}")
                        if student:
                            parts.append(f"学生活动：{student}")
                        if intent:
                            parts.append(f"设计意图：{intent}")

                        step_texts.append("\n".join(parts))

                processed["teaching_steps_text"] = "\n\n".join(step_texts)
            elif isinstance(steps, str):
                processed["teaching_steps"] = steps
                processed["teaching_steps_text"] = steps
            else:
                processed["teaching_steps"] = []
                processed["teaching_steps_text"] = ""

        # Process homework
        if "homework" in data:
            homework = data["homework"]
            if isinstance(homework, dict):
                processed["homework"] = homework
                processed["homework_required"] = homework.get("required", "")
                processed["homework_optional"] = homework.get("optional", "")
            elif isinstance(homework, str):
                processed["homework"] = homework
            else:
                processed["homework"] = ""

        # Add common field aliases for template compatibility
        if "topic" in data:
            processed["teaching_topic"] = data["topic"]
        if "duration" in data:
            processed["teaching_hours"] = data["duration"]
        if "grade" in data:
            processed["class_name"] = data["grade"]
        if "teaching_methods" in data:
            processed["teaching_methods_content"] = data["teaching_methods"]
        if "teaching_tools" in data:
            processed["teaching_materials"] = data["teaching_tools"]

        # Copy all other fields from original data
        for key in [
            "subject", "grade", "topic", "duration",
            "key_points", "difficult_points",
            "teaching_methods", "teaching_tools",
            "student_analysis", "textbook_analysis",
            "blackboard_design", "reflection",
            "week_number", "location", "references",
            "ideological_political"
        ]:
            if key in data and key not in processed:
                value = data[key]
                processed[key] = value if value is not None else ""

        return processed


def render_lesson_plan(
    template_path: str,
    lesson_plan_data: Dict[str, Any],
) -> str:
    """
    Convenience function to render a lesson plan.

    Args:
        template_path: Path to the template file
        lesson_plan_data: Complete lesson plan data

    Returns:
        Path to the generated document
    """
    renderer = DocumentRenderer()
    return renderer.render_lesson_plan(template_path, lesson_plan_data)
