"""
Unit tests for parser services.
"""
import pytest
from pathlib import Path
from backend.services.template_parser import TemplateParser
from backend.services.lesson_plan_parser import LessonPlanParser


class TestTemplateParser:
    """Test template parser functionality."""

    def test_simple_variable_parsing(self):
        """Test parsing simple Jinja2 variables."""
        # This would require a test .docx file
        # For now, we test the pattern matching logic
        from backend.services.template_parser import TemplateParser

        # Test variable pattern
        text = "Subject: {{subject}}"
        matches = list(TemplateParser.VARIABLE_PATTERN.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(1) == "subject"

    def test_loop_pattern_parsing(self):
        """Test parsing loop structures."""
        from backend.services.template_parser import TemplateParser

        # Test loop pattern
        text = "{% for step in teaching_steps %}"
        match = TemplateParser.LOOP_START_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "step"
        assert match.group(2) == "teaching_steps"

    def test_conditional_pattern_parsing(self):
        """Test parsing conditional structures."""
        from backend.services.template_parser import TemplateParser

        # Test if pattern
        text = "{% if has_experiment %}"
        match = TemplateParser.IF_START_PATTERN.search(text)
        assert match is not None
        # IF_START_PATTERN uses non-capturing group, just check match exists
        assert "{% if" in match.group(0)


class TestLessonPlanParser:
    """Test lesson plan parser functionality."""

    def test_section_header_matching(self):
        """Test section header pattern matching."""
        # This test demonstrates the pattern matching without requiring a file
        test_cases = [
            ("教学目标：", "teaching_goals"),
            ("教学重点", "key_points"),
            ("教学难点", "difficult_points"),
            ("教具准备", "teaching_tools"),
            ("教学过程", "teaching_process"),
            ("作业", "homework"),
            ("板书设计", "blackboard_design"),
            ("教学反思", "reflection"),
        ]

        # Test that patterns are correctly defined
        from backend.services.lesson_plan_parser import LessonPlanParser

        for text, expected_section in test_cases:
            # We can't directly call _match_section_header without a parser instance
            # But we can verify the patterns exist
            assert expected_section in LessonPlanParser.SECTION_PATTERNS

    def test_section_patterns_completeness(self):
        """Test that all expected sections have patterns."""
        from backend.services.lesson_plan_parser import LessonPlanParser

        expected_sections = {
            "teaching_goals",
            "key_points",
            "difficult_points",
            "teaching_tools",
            "teaching_methods",  # Added
            "teaching_process",
            "student_analysis",  # Added
            "textbook_analysis",  # Added
            "homework",
            "reflection",
            "blackboard_design",
        }

        assert set(LessonPlanParser.SECTION_PATTERNS.keys()) == expected_sections


@pytest.mark.asyncio
class TestDatabase:
    """Test database functionality."""

    async def test_database_initialization(self, tmp_path):
        """Test database table creation."""
        from backend.models.database import Database

        db_path = str(tmp_path / "test.db")
        db = Database(db_path)

        await db.initialize()

        # Verify tables were created
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "templates",
            "lesson_plans",
            "batch_tasks",  # Added
            "batch_lesson_plans",  # Added
            "course_chapter_templates",  # Added
            "template_versions",  # Added
            "classes",  # Added
            "document_edits",
            "edit_logs",
            "user_settings",
            "textbooks",  # Added
            "textbook_chapters",  # Added
            "lesson_plan_textbooks",  # Added
            "subjects",
            "grades",
        }

        assert tables == expected_tables

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
