"""
Document renderer service for generating new lesson plans from templates.

Uses pure text replacement to preserve the original document format.
Only replaces {{placeholder}} patterns without processing Jinja2 loops/conditions.
"""
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import copy
import re
from docx import Document
from docx.shared import Pt

from ..config import settings


class DocumentRenderer:
    """
    Render Word documents from templates using pure text replacement.

    This approach preserves the original document structure by only replacing
    {{placeholder}} text without interpreting Jinja2 control structures.
    """

    def __init__(self):
        """Initialize the document renderer."""
        self.template_dir = settings.template_dir
        self.output_dir = settings.output_dir

    def render_new_document(
        self,
        template_path: str,
        data: Dict[str, Any],
        output_filename: Optional[str] = None,
    ) -> str:
        """
        Render a new lesson plan document from a template.

        Args:
            template_path: Path to the template file
            data: Dictionary of data to fill the template
            output_filename: Optional output filename

        Returns:
            Path to the generated document
        """
        # Load the template using python-docx
        doc = Document(template_path)

        # Process data for rendering
        processed_data = self._process_data(data)

        # Replace placeholders in document
        self._replace_placeholders(doc, processed_data)

        # Generate output path
        if output_filename is None:
            topic = data.get("topic", "教案")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{topic}_{timestamp}.docx"

        output_path = str(self.output_dir / output_filename)

        # Save the document
        doc.save(output_path)

        return output_path

    def _replace_placeholders(self, doc: Document, data: Dict[str, Any]) -> None:
        """
        Replace all {{placeholder}} patterns in the document with actual values.
        
        This method:
        1. Replaces placeholders in paragraphs
        2. Replaces placeholders in table cells
        3. Removes unprocessed Jinja2 control structures ({% ... %})
        4. Preserves all original formatting
        """
        # Pattern for simple placeholders: {{variable}} or {{object.property}}
        placeholder_pattern = re.compile(r'\{\{([^}]+)\}\}')
        # Pattern for Jinja2 control structures: {% ... %}
        control_pattern = re.compile(r'\{%[^%]*%\}')

        def get_value(key: str) -> str:
            """Get a value from data dict, supporting dot notation."""
            key = key.strip()
            if '.' in key:
                parts = key.split('.')
                value = data
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part, '')
                    else:
                        return ''
                return str(value) if value else ''
            return str(data.get(key, '')) if data.get(key) is not None else ''

        def replace_in_text(text: str) -> str:
            """Replace placeholders in a text string."""
            # First, replace simple placeholders
            def replace_placeholder(match):
                key = match.group(1)
                return get_value(key)
            
            result = placeholder_pattern.sub(replace_placeholder, text)
            
            # Then, remove Jinja2 control structures (they can't be processed)
            result = control_pattern.sub('', result)
            
            # Clean up any resulting empty lines or excessive whitespace
            lines = [line for line in result.split('\n') if line.strip()]
            return '\n'.join(lines) if lines else result

        def replace_in_paragraph(paragraph) -> None:
            """Replace placeholders in a paragraph while preserving formatting."""
            full_text = paragraph.text
            if not full_text:
                return
                
            # Check if there are any placeholders or control structures
            if not (placeholder_pattern.search(full_text) or control_pattern.search(full_text)):
                return
            
            # Get the replaced text
            new_text = replace_in_text(full_text)
            
            # If text hasn't changed, skip
            if new_text == full_text:
                return
            
            # Clear existing runs and add new text with first run's formatting
            if paragraph.runs:
                # Save the formatting of the first run
                first_run = paragraph.runs[0]
                font_name = first_run.font.name
                font_size = first_run.font.size
                font_bold = first_run.font.bold
                font_italic = first_run.font.italic
                
                # Clear all runs
                for run in paragraph.runs:
                    run.text = ''
                
                # Set new text in first run
                first_run.text = new_text
                
                # Restore formatting
                first_run.font.name = font_name
                first_run.font.size = font_size
                first_run.font.bold = font_bold
                first_run.font.italic = font_italic
            else:
                # No runs, just set the text directly
                paragraph.text = new_text

        def replace_in_cell(cell) -> None:
            """Replace placeholders in a table cell."""
            for paragraph in cell.paragraphs:
                replace_in_paragraph(paragraph)

        # Replace in main document paragraphs
        for paragraph in doc.paragraphs:
            replace_in_paragraph(paragraph)

        # Replace in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    replace_in_cell(cell)

        # Replace in headers
        for section in doc.sections:
            if section.header:
                for paragraph in section.header.paragraphs:
                    replace_in_paragraph(paragraph)
            if section.footer:
                for paragraph in section.footer.paragraphs:
                    replace_in_paragraph(paragraph)

    def _process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data for template filling.

        Converts complex data structures (dicts, lists) into string representations
        suitable for direct text replacement.
        """
        processed = {}

        # Process teaching_goals
        if "teaching_goals" in data and isinstance(data["teaching_goals"], dict):
            value = data["teaching_goals"]
            knowledge_list = value.get("knowledge", [])
            ability_list = value.get("ability", [])
            emotion_list = value.get("emotion", [])
            
            # Format as numbered lists
            knowledge_text = "\n".join(f"{i+1}. {g}" for i, g in enumerate(knowledge_list)) if knowledge_list else ""
            ability_text = "\n".join(f"{i+1}. {g}" for i, g in enumerate(ability_list)) if ability_list else ""
            emotion_text = "\n".join(f"{i+1}. {g}" for i, g in enumerate(emotion_list)) if emotion_list else ""

            # Store as nested dict for dot notation access
            processed["teaching_goals"] = {
                "knowledge": knowledge_text,
                "ability": ability_text,
                "emotion": emotion_text,
            }
            
            # Also store as flat keys for alternative template formats
            processed["knowledge"] = knowledge_text
            processed["ability"] = ability_text
            processed["emotion"] = emotion_text
            processed["knowledge_objectives"] = knowledge_text
            processed["ability_objectives"] = ability_text
            processed["quality_objectives"] = emotion_text

            # Combined format
            goals_parts = []
            if knowledge_text:
                goals_parts.append(f"知识目标：\n{knowledge_text}")
            if ability_text:
                goals_parts.append(f"能力目标：\n{ability_text}")
            if emotion_text:
                goals_parts.append(f"素质目标：\n{emotion_text}")
            processed["teaching_goals_text"] = "\n\n".join(goals_parts)

        # Process teaching_steps
        if "teaching_steps" in data and isinstance(data["teaching_steps"], list):
            steps = data["teaching_steps"]
            
            # Format all steps as a single text block
            step_texts = []
            for i, step in enumerate(steps):
                if isinstance(step, dict):
                    stage = step.get("stage", "")
                    duration = step.get("duration", "")
                    teacher = step.get("teacher_activity", "")
                    student = step.get("student_activity", "")
                    intent = step.get("design_intent", "")
                    
                    parts = []
                    if stage:
                        parts.append(f"【{stage}】")
                    if duration:
                        parts.append(f"时长：{duration}")
                    if teacher:
                        parts.append(f"教师活动：{teacher}")
                    if student:
                        parts.append(f"学生活动：{student}")
                    if intent:
                        parts.append(f"设计意图：{intent}")
                    
                    step_texts.append("\n".join(parts))
            
            processed["teaching_steps_text"] = "\n\n".join(step_texts)
            
            # Also create individual step placeholders for templates with specific cells
            # Format for templates that expect step.teacher_activity, step.student_activity
            combined_teacher = []
            combined_student = []
            for step in steps:
                if isinstance(step, dict):
                    stage = step.get("stage", "")
                    teacher = step.get("teacher_activity", "")
                    student = step.get("student_activity", "")
                    if stage and teacher:
                        combined_teacher.append(f"【{stage}】\n{teacher}")
                    elif teacher:
                        combined_teacher.append(teacher)
                    if stage and student:
                        combined_student.append(f"【{stage}】\n{student}")
                    elif student:
                        combined_student.append(student)
            
            processed["step"] = {
                "teacher_activity": "\n\n".join(combined_teacher),
                "student_activity": "\n\n".join(combined_student),
            }

        # Process homework
        if "homework" in data and isinstance(data["homework"], dict):
            value = data["homework"]
            required = value.get("required", "")
            optional = value.get("optional", "")

            # Store as nested dict
            processed["homework"] = {
                "required": required,
                "optional": optional,
            }
            
            # Also store flat keys
            processed["homework_required"] = required
            processed["homework_optional"] = optional

        # Process all other fields
        for key, value in data.items():
            if key in ["teaching_goals", "teaching_steps", "homework"]:
                continue  # Already processed

            if isinstance(value, str):
                processed[key] = value
            elif isinstance(value, list):
                # Convert lists to newline-separated strings
                processed[key] = "\n".join(str(v) for v in value if v)
            elif value is None:
                processed[key] = ""
            elif isinstance(value, dict):
                # Store dicts for dot notation access
                processed[key] = value
            else:
                processed[key] = str(value)

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

        # Ensure g placeholder has content (for templates with {% for g in ... %})
        # Since we remove the for loops, we need to provide the content directly
        if "teaching_goals" in processed and isinstance(processed["teaching_goals"], dict):
            processed["g"] = ""  # Empty, the content is in teaching_goals.knowledge etc.

        return processed

    def render_lesson_plan(
        self,
        template_path: str,
        lesson_plan_data: Dict[str, Any],
    ) -> str:
        """
        Render a complete lesson plan.

        Args:
            template_path: Path to the template file
            lesson_plan_data: Complete lesson plan data with all sections

        Returns:
            Path to the generated document
        """
        # Extract topic for filename
        topic = lesson_plan_data.get("topic", "教案")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{topic}_{timestamp}.docx"

        return self.render_new_document(
            template_path=template_path,
            data=lesson_plan_data,
            output_filename=output_filename,
        )

    def render_teaching_goals(
        self,
        knowledge_goals: list[str],
        ability_goals: list[str],
        emotion_goals: list[str],
    ) -> str:
        """
        Format teaching goals for template rendering.

        Args:
            knowledge_goals: Knowledge and skill goals
            ability_goals: Process and method goals
            emotion_goals: Emotional attitude goals

        Returns:
            Formatted goals string
        """
        lines = []

        if knowledge_goals:
            lines.append("知识与技能：")
            lines.extend(f"  {i+1}. {goal}" for i, goal in enumerate(knowledge_goals))

        if ability_goals:
            lines.append("\n过程与方法：")
            lines.extend(f"  {i+1}. {goal}" for i, goal in enumerate(ability_goals))

        if emotion_goals:
            lines.append("\n情感态度与价值观：")
            lines.extend(f"  {i+1}. {goal}" for i, goal in enumerate(emotion_goals))

        return "\n".join(lines)

    def render_teaching_steps(
        self, steps: list[Dict[str, str]]
    ) -> list[Dict[str, str]]:
        """
        Format teaching steps for template rendering.

        Args:
            steps: List of teaching step dictionaries

        Returns:
            Formatted steps list
        """
        formatted_steps = []

        for step in steps:
            formatted_step = {
                "stage": step.get("stage", ""),
                "duration": step.get("duration", ""),
                "teacher_activity": step.get("teacher_activity", ""),
                "student_activity": step.get("student_activity", ""),
                "design_intent": step.get("design_intent", ""),
            }
            formatted_steps.append(formatted_step)

        return formatted_steps

    def render_homework(
        self, required: str, optional: Optional[str] = None
    ) -> str:
        """
        Format homework for template rendering.

        Args:
            required: Required homework
            optional: Optional homework

        Returns:
            Formatted homework string
        """
        lines = [f"必做：{required}"]
        if optional:
            lines.append(f"\n选做：{optional}")
        return "\n".join(lines)


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
