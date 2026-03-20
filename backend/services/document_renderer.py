"""
Document renderer service for generating lesson plans from templates.

Uses docxtpl (not python-docx) for template rendering to preserve document structure.
See WORD_EXPORT_FIX.md for details.
"""
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from docxtpl import DocxTemplate
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from ..config import settings

logger = logging.getLogger(__name__)


class DocumentRenderer:
    """
    Render Word documents from templates using docxtpl.

    This approach properly renders Jinja2 templates while preserving
    the original document structure, including tables and formatting.
    """
    _MARKDOWN_TOKENS = ("[", "](", "![", "**", "__", "`", "~~", "*", "_", "#")
    _LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^)]+\)')
    _IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\([^)]+\)')
    _BOLD_ASTERISK_PATTERN = re.compile(r'\*\*([^*]+)\*\*')
    _BOLD_UNDERSCORE_PATTERN = re.compile(r'__([^_]+)__')
    _ITALIC_ASTERISK_PATTERN = re.compile(r'(?<!\*)\*([^*]+)\*(?!\*)')
    _ITALIC_UNDERSCORE_PATTERN = re.compile(r'(?<!_)_([^_]+)_(?!_)')
    _HEADER_PATTERN = re.compile(r'^#+\s+', flags=re.MULTILINE)
    _STRIKE_PATTERN = re.compile(r'~~([^~]+)~~')
    _INLINE_CODE_PATTERN = re.compile(r'`([^`]+)`')
    _WHITESPACE_CLEANUP_PATTERN = re.compile(r'[ \t]{2,}')

    def __init__(self):
        """Initialize the document renderer."""
        self.template_dir = settings.template_dir
        self.output_dir = settings.output_dir

    def _parse_duration_number(self, duration: str) -> float:
        """
        Parse numeric value from duration string.
        Examples: "2课时" -> 2.0, "1.5课时" -> 1.5, "45分钟" -> 45

        Args:
            duration: Duration string with number and unit

        Returns:
            Numeric value as float
        """
        if not duration or not isinstance(duration, str):
            return 0.0

        # Match number (including decimals) at the start of string
        match = re.match(r'^(\d+(?:\.\d+)?)', duration.strip())
        if match:
            return float(match.group(1))

        return 0.0

    def _strip_markdown(self, text: str) -> str:
        """
        Clean markdown formatting markers from text to make it suitable for Word documents.

        Args:
            text: Text that may contain markdown formatting

        Returns:
            Text with markdown markers removed, content preserved

        Cleaning rules:
        - **bold** → bold (preserve content)
        - *italic* → italic
        - # Header → Header
        - ## Header → Header
        - [text](url) → text
        """
        if not text or not isinstance(text, str):
            return text or ""

        # Cleaning order matters - from complex to simple patterns

        # 1. Clean links [text](url) → text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # 2. Clean images ![alt](url) → alt
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)

        # 3. Clean bold **text** or __text__
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)

        # 4. Clean italic *text* or _text_ (avoid matching already cleaned bold)
        text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', text)
        text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', text)

        # 5. Clean headers # ## ### etc (at line start)
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        # 6. Clean strikethrough ~~text~~
        text = re.sub(r'~~([^~]+)~~', r'\1', text)

        # 7. Clean inline code `code`
        text = re.sub(r'`([^`]+)`', r'\1', text)

        return text

    def _clean_text_for_output(self, text: str) -> str:
        """
        Fast-path clean for plain text and markdown clean for rich text.
        """
        if not text or not isinstance(text, str):
            return text or ""

        if any(token in text for token in self._MARKDOWN_TOKENS):
            text = self._strip_markdown(text)

        return self._normalize_subheading_line_breaks(text)

    def _normalize_subheading_line_breaks(self, text: str) -> str:
        """
        Ensure inline subheadings are moved to a new line for readability.
        """
        if not text or not isinstance(text, str):
            return text or ""

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        normalized = re.sub(r'([。！？；:：])\s*(#{1,6}\s+)', r'\1\n\2', normalized)
        normalized = re.sub(r'([。！？；:：])\s*([一二三四五六七八九十]+、)', r'\1\n\2', normalized)
        normalized = re.sub(r'([。！？；:：])\s*([（(][一二三四五六七八九十]+[)）])', r'\1\n\2', normalized)
        normalized = re.sub(r'([。！？；:：])\s*((?:\d{1,2}[\.、]))', r'\1\n\2', normalized)
        normalized = self._WHITESPACE_CLEANUP_PATTERN.sub(' ', normalized)

        lines = [line.strip() for line in normalized.split("\n")]
        cleaned_lines = []

        for index, line in enumerate(lines):
            if line:
                cleaned_lines.append(line)
                continue

            previous_line = cleaned_lines[-1] if cleaned_lines else ""
            next_line = ""
            for candidate in lines[index + 1:]:
                if candidate:
                    next_line = candidate.strip()
                    break

            # Drop empty lines around short heading-like labels and subheadings.
            if self._is_heading_like_line(previous_line) or self._is_heading_like_line(next_line):
                continue

            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

        return "\n".join(cleaned_lines).strip()

    @staticmethod
    def _is_heading_like_line(line: str) -> bool:
        if not line:
            return False

        stripped = line.strip()

        if re.match(r'^(#{1,6}\s+)', stripped):
            return True

        if re.match(r'^([一二三四五六七八九十]+、|[（(][一二三四五六七八九十]+[)）]|\d{1,2}[\.、])', stripped):
            return True

        if len(stripped) <= 20 and re.match(r'^[^。！？]{1,20}[：:]$', stripped):
            return True

        return False

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

    def render_lesson_plans_document(
        self,
        template_path: str,
        lesson_plans_data: List[Dict[str, Any]],
        course_name: str,
        document_number: int,
        week_number: int = 1,
    ) -> str:
        """
        Render multiple lesson plans into a single document with continuous layout.

        This is used for batch generation where each document contains
        multiple lesson plans (default 2).

        Args:
            template_path: Path to the template file
            lesson_plans_data: List of lesson plan data dictionaries
            course_name: Course name for file naming
            document_number: Document sequence number (1, 2, 3...)
            week_number: Week number for display (default 1)

        Returns:
            Path to the generated document (named: 第1周_course_name_01.docx)
        """
        if not lesson_plans_data:
            raise ValueError("lesson_plans_data cannot be empty")

        # Render each lesson plan to a temporary document
        temp_docs = []
        for idx, lesson_data in enumerate(lesson_plans_data):
            # Add lesson_number to the title if not already present
            lesson_number = lesson_data.get("lesson_number")
            if lesson_number:
                # Update topic to include lesson number in title
                original_topic = lesson_data.get("topic", "")
                lesson_data["lesson_title"] = f"教案{lesson_number}：{original_topic}"
            else:
                lesson_data["lesson_title"] = lesson_data.get("topic", "")

            # Process data
            processed_data = self._process_data(lesson_data)

            # Ensure lesson_title is in processed data
            processed_data["lesson_title"] = lesson_data.get("lesson_title", lesson_data.get("topic", ""))

            # Handle None values
            for key, value in list(processed_data.items()):
                if value is None:
                    processed_data[key] = []
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_value is None:
                            value[sub_key] = []

            # Load and render template
            template = DocxTemplate(template_path)
            template.render(processed_data)

            # Save to temporary path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"_temp_{course_name}_{document_number}_{idx}_{timestamp}.docx"
            temp_path = str(self.output_dir / temp_filename)
            template.save(temp_path)
            temp_docs.append(temp_path)

        # Combine documents (continuous layout, no page breaks)
        output_path = self._combine_documents_continuous(
            temp_docs, course_name, document_number, week_number
        )

        # Clean up temporary files
        for temp_path in temp_docs:
            try:
                Path(temp_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_path}: {e}")

        return output_path

    def _combine_documents_continuous(
        self,
        doc_paths: List[str],
        course_name: str,
        document_number: int,
        week_number: int = 1,
    ) -> str:
        """
        Combine multiple documents into one (continuous layout, no page breaks).

        This follows the reference template format where multiple lesson plans
        are placed continuously in the same document.

        Args:
            doc_paths: List of paths to documents to combine
            course_name: Course name for output filename
            document_number: Document sequence number (1, 2, 3...)
            week_number: Week number for display (default 1)

        Returns:
            Path to the combined document (named: 第1周_course_name_01.docx)
        """
        if len(doc_paths) == 0:
            raise ValueError("No documents to combine")

        # Generate output filename: 第1周_course_name_01.docx
        week_display = f"第{week_number}周"
        output_filename = f"{week_display}_{course_name}_{document_number:02d}.docx"
        output_path = str(self.output_dir / output_filename)

        if len(doc_paths) == 1:
            # Only one document, just copy it
            import shutil
            shutil.copy(doc_paths[0], output_path)
            return output_path

        # Load the first document as base
        combined_doc = Document(doc_paths[0])

        # Append remaining documents WITHOUT page breaks (continuous layout)
        for doc_path in doc_paths[1:]:
            # Load the document to append
            sub_doc = Document(doc_path)

            # Copy all body elements directly (no page break)
            for element in sub_doc.element.body:
                # Skip sectPr (section properties) as we don't want multiple sections
                if element.tag.endswith('sectPr'):
                    continue
                combined_doc.element.body.append(element)

        # Save combined document
        combined_doc.save(output_path)

        logger.info(f"Combined {len(doc_paths)} lesson plans into: {output_path}")

        return output_path

    def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data for template filling.

        Converts complex data structures into formats suitable for Jinja2 rendering.
        Also strips markdown formatting from text content.
        """
        processed = {}

        # Copy all simple fields with markdown cleaning
        for key, value in data.items():
            if isinstance(value, str):
                processed[key] = self._clean_text_for_output(value)
            elif isinstance(value, (int, float, bool)) or value is None:
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
                # Clean markdown from each step's text fields
                cleaned_steps = []
                for step in steps:
                    if isinstance(step, dict):
                        cleaned_step = {}
                        for key, value in step.items():
                            if isinstance(value, str):
                                cleaned_step[key] = self._clean_text_for_output(value)
                            else:
                                cleaned_step[key] = value
                        cleaned_steps.append(cleaned_step)
                    else:
                        cleaned_steps.append(step)
                processed["teaching_steps"] = cleaned_steps

                # Also create combined text versions for templates without loops
                step_texts = []
                for i, step in enumerate(cleaned_steps):
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
                processed["teaching_steps"] = self._clean_text_for_output(steps)
                processed["teaching_steps_text"] = self._clean_text_for_output(steps)
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
            # Also add numeric duration for templates that only need the number
            duration_value = self._parse_duration_number(data["duration"])
            processed["duration_hours"] = duration_value
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
            "ideological_political", "class_name",
            "online_resources", "textbook_name"
        ]:
            if key in data and key not in processed:
                value = data[key]
                processed[key] = value if value is not None else ""

        # Add field aliases for template compatibility
        # Map online_resources to electronic_resources for Yunnan template
        if "online_resources" in data:
            processed["electronic_resources"] = data["online_resources"] or ""

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
