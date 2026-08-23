"""
Database models and connection management.
"""
import aiosqlite
import sqlite3
from pathlib import Path
from typing import AsyncIterator, Optional
from contextlib import asynccontextmanager

from ..config import settings


class Database:
    """Database connection manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Initialize database and create tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await self._create_tables(db)
            await db.commit()

    async def _create_tables(self, db: aiosqlite.Connection) -> None:
        """Create all database tables."""

        # Templates table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                subject TEXT,
                grade TEXT,
                file_path TEXT NOT NULL,
                fields_config TEXT,
                preview_image TEXT,
                use_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Lesson plans table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lesson_plans (
                id TEXT PRIMARY KEY,
                template_id TEXT,
                title TEXT NOT NULL,
                subject TEXT,
                grade TEXT,
                topic TEXT,
                input_data TEXT,
                generated_content TEXT,
                final_content TEXT,
                output_file_path TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES templates(id)
            )
        """)

        # Document edits table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS document_edits (
                id TEXT PRIMARY KEY,
                original_file_path TEXT NOT NULL,
                original_file_name TEXT NOT NULL,
                parsed_content TEXT,
                edit_history TEXT,
                current_file_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Edit logs table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS edit_logs (
                id TEXT PRIMARY KEY,
                document_edit_id TEXT,
                section_name TEXT,
                operation_type TEXT,
                original_content TEXT,
                new_content TEXT,
                ai_prompt TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_edit_id) REFERENCES document_edits(id)
            )
        """)

        # User settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Batch tasks table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS batch_tasks (
                id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                grade TEXT NOT NULL,
                template_id TEXT NOT NULL,
                total_hours INTEGER NOT NULL,
                hours_per_lesson INTEGER DEFAULT 2,
                chapters TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                total_count INTEGER NOT NULL,
                completed_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                zip_file_path TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (template_id) REFERENCES templates(id)
            )
        """)

        # Batch lesson plans table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS batch_lesson_plans (
                id TEXT PRIMARY KEY,
                batch_task_id TEXT NOT NULL,
                lesson_plan_id TEXT NOT NULL,
                lesson_number INTEGER NOT NULL,
                topic TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                file_path TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_task_id) REFERENCES batch_tasks(id),
                FOREIGN KEY (lesson_plan_id) REFERENCES lesson_plans(id)
            )
        """)

        # Course chapter templates table (for caching AI-generated chapters)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS course_chapter_templates (
                id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                grade TEXT NOT NULL,
                total_hours INTEGER NOT NULL,
                hours_per_lesson INTEGER DEFAULT 2,
                chapters TEXT NOT NULL,
                use_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_name, subject, grade, total_hours, hours_per_lesson)
            )
        """)

        # Standalone semester plans (teaching/experiment) derived from lesson plans
        await db.execute("""
            CREATE TABLE IF NOT EXISTS course_plans (
                id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                grade TEXT NOT NULL DEFAULT '',
                class_names TEXT NOT NULL DEFAULT '',
                academic_year TEXT NOT NULL DEFAULT '',
                semester INTEGER NOT NULL DEFAULT 0,
                teacher_name TEXT NOT NULL DEFAULT '',
                hours_per_lesson INTEGER NOT NULL DEFAULT 2,
                start_week INTEGER NOT NULL DEFAULT 1,
                total_hours INTEGER NOT NULL DEFAULT 0,
                location TEXT NOT NULL DEFAULT '',
                plan_date TEXT NOT NULL DEFAULT '',
                first_class_date TEXT NOT NULL DEFAULT '',
                class_periods TEXT NOT NULL DEFAULT '',
                class_schedules TEXT NOT NULL DEFAULT '[]',
                plan_types TEXT NOT NULL DEFAULT '[]',
                chapters TEXT NOT NULL DEFAULT '[]',
                source_lesson_plan_ids TEXT NOT NULL DEFAULT '[]',
                status TEXT DEFAULT 'draft',
                output_files TEXT NOT NULL DEFAULT '[]',
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._add_column_if_not_exists(
            db, "course_plans", "error_message", "TEXT"
        )

        # Add batch-related columns to lesson_plans if they don't exist
        await self._add_column_if_not_exists(
            db, "lesson_plans", "batch_task_id", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "lesson_plans", "lesson_number", "INTEGER"
        )
        await self._add_column_if_not_exists(
            db, "lesson_plans", "status", "TEXT DEFAULT 'draft'"
        )

        # Add hours-based columns to batch_tasks if upgrading from week-based
        await self._add_column_if_not_exists(
            db, "batch_tasks", "total_hours", "INTEGER"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "hours_per_lesson", "INTEGER DEFAULT 2"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "status", "TEXT DEFAULT 'pending'"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "total_count", "INTEGER DEFAULT 0"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "completed_count", "INTEGER DEFAULT 0"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "failed_count", "INTEGER DEFAULT 0"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "zip_file_path", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "error_message", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "completed_at", "TEXT"
        )

        # Add hours-based columns to course_chapter_templates if upgrading
        await self._add_column_if_not_exists(
            db, "course_chapter_templates", "total_hours", "INTEGER"
        )
        await self._add_column_if_not_exists(
            db, "course_chapter_templates", "hours_per_lesson", "INTEGER DEFAULT 2"
        )

        # Add lesson_number column to batch_lesson_plans if upgrading
        await self._add_column_if_not_exists(
            db, "batch_lesson_plans", "lesson_number", "INTEGER"
        )
        await self._add_column_if_not_exists(
            db, "batch_lesson_plans", "status", "TEXT DEFAULT 'pending'"
        )
        await self._add_column_if_not_exists(
            db, "batch_lesson_plans", "error_message", "TEXT"
        )

        # Classes table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Template versions table (for version history)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS template_versions (
                id TEXT PRIMARY KEY,
                template_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                user TEXT DEFAULT '系统',
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
            )
        """)

        # Create index for template_versions
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_template_versions_template_id
            ON template_versions(template_id)
        """)

        # Textbooks table (for教材management)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS textbooks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                isbn TEXT,
                author TEXT,
                publisher TEXT,
                edition TEXT,
                subject TEXT,
                grade TEXT,
                cover_image TEXT,
                description TEXT,
                status TEXT DEFAULT 'active',
                use_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Provenance for externally discovered textbook metadata and catalogs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS textbook_sources (
                id TEXT PRIMARY KEY,
                textbook_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT,
                external_id TEXT,
                confidence REAL DEFAULT 0,
                raw_metadata TEXT,
                retrieved_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (textbook_id) REFERENCES textbooks(id) ON DELETE CASCADE
            )
        """)

        # Textbook chapters table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS textbook_chapters (
                id TEXT PRIMARY KEY,
                textbook_id TEXT NOT NULL,
                chapter_number TEXT NOT NULL,
                chapter_title TEXT NOT NULL,
                content_summary TEXT,
                key_concepts TEXT,
                sort_order INTEGER DEFAULT 0,
                hours_required INTEGER,
                parent_chapter_id TEXT,
                source_id TEXT,
                content_origin TEXT DEFAULT 'manual',
                confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (textbook_id) REFERENCES textbooks(id) ON DELETE CASCADE,
                FOREIGN KEY (source_id) REFERENCES textbook_sources(id) ON DELETE SET NULL
            )
        """)

        # Add provenance columns when upgrading an existing database.
        await self._add_column_if_not_exists(
            db, "textbook_chapters", "source_id", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "textbook_chapters", "content_origin", "TEXT DEFAULT 'manual'"
        )
        await self._add_column_if_not_exists(
            db, "textbook_chapters", "confidence", "REAL"
        )

        # Lesson plan textbooks association table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lesson_plan_textbooks (
                id TEXT PRIMARY KEY,
                lesson_plan_id TEXT NOT NULL,
                textbook_id TEXT NOT NULL,
                chapter_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lesson_plan_id) REFERENCES lesson_plans(id) ON DELETE CASCADE,
                FOREIGN KEY (textbook_id) REFERENCES textbooks(id) ON DELETE CASCADE,
                FOREIGN KEY (chapter_id) REFERENCES textbook_chapters(id) ON DELETE SET NULL
            )
        """)

        # Create indexes for textbooks
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbooks_subject_grade
            ON textbooks(subject, grade)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbooks_name
            ON textbooks(name)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbooks_isbn
            ON textbooks(isbn)
        """)

        # Create indexes for textbook_chapters
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbook_chapters_textbook_id
            ON textbook_chapters(textbook_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbook_chapters_sort_order
            ON textbook_chapters(textbook_id, sort_order)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbook_sources_textbook_id
            ON textbook_sources(textbook_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbook_sources_external
            ON textbook_sources(source_type, external_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_textbook_chapters_source_id
            ON textbook_chapters(source_id)
        """)

        # Create indexes for lesson_plan_textbooks
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lesson_plan_textbooks_lesson
            ON lesson_plan_textbooks(lesson_plan_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lesson_plan_textbooks_textbook
            ON lesson_plan_textbooks(textbook_id)
        """)

        # Subjects table (for subject management)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                is_preset INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for subjects
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_subjects_category
            ON subjects(category)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_subjects_name
            ON subjects(name)
        """)

        # Grades table (for grade management)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                is_preset INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for grades
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_grades_category
            ON grades(category)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_grades_name
            ON grades(name)
        """)

        # Add start_week and class_ids to batch_tasks
        await self._add_column_if_not_exists(
            db, "batch_tasks", "start_week", "INTEGER DEFAULT 1"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "class_ids", "TEXT"
        )

        # Add additional batch task fields for location, textbook, resources
        await self._add_column_if_not_exists(
            db, "batch_tasks", "location", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "textbook_name", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "online_resources", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "generate_reflection", "INTEGER DEFAULT 0"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "class_names", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "supplemental_artifacts", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "academic_year", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "semester", "INTEGER"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "teacher_name", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "plan_date", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "first_class_date", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "class_periods", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "experiment_schedules", "TEXT"
        )

        # Add class_ids to lesson_plans
        await self._add_column_if_not_exists(
            db, "lesson_plans", "class_ids", "TEXT"
        )

        # Add task_type to batch_tasks (for draft vs normal tasks)
        await self._add_column_if_not_exists(
            db, "batch_tasks", "task_type", "TEXT DEFAULT 'normal'"
        )

        # Add textbook_id to batch_tasks (for textbook integration)
        await self._add_column_if_not_exists(
            db, "batch_tasks", "textbook_id", "TEXT"
        )

        # Add textbook_id to lesson_plans (for textbook integration)
        await self._add_column_if_not_exists(
            db, "lesson_plans", "textbook_id", "TEXT"
        )

        # Create index for batch_tasks textbook association
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_tasks_textbook
            ON batch_tasks(textbook_id)
        """)

        # Create index for lesson_plans textbook association
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lesson_plans_textbook
            ON lesson_plans(textbook_id)
        """)

        # Create indexes for lesson plan draft management
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lesson_plans_status_template
            ON lesson_plans(status, template_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_tasks_type_status
            ON batch_tasks(task_type, status)
        """)

        # Teaching resource library
        await db.execute("""
            CREATE TABLE IF NOT EXISTS teaching_resources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                subject TEXT,
                grade TEXT,
                content TEXT NOT NULL,
                source_url TEXT,
                tags TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                use_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Course and semester archives provide a reusable preparation context.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS course_archives (
                id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                grade TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                semester INTEGER NOT NULL,
                teacher_name TEXT,
                textbook_id TEXT,
                total_hours INTEGER DEFAULT 32,
                hours_per_lesson INTEGER DEFAULT 2,
                start_week INTEGER DEFAULT 1,
                class_ids TEXT DEFAULT '[]',
                location TEXT,
                notes TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (textbook_id) REFERENCES textbooks(id) ON DELETE SET NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS course_archive_resources (
                archive_id TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (archive_id, resource_id),
                FOREIGN KEY (archive_id) REFERENCES course_archives(id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES teaching_resources(id) ON DELETE CASCADE
            )
        """)

        await self._add_column_if_not_exists(
            db, "batch_tasks", "course_archive_id", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "resource_ids", "TEXT DEFAULT '[]'"
        )
        await self._add_column_if_not_exists(
            db, "lesson_plans", "course_archive_id", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "lesson_plans", "resource_ids", "TEXT DEFAULT '[]'"
        )

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_teaching_resources_filters
            ON teaching_resources(status, resource_type, subject, grade)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_course_archives_term
            ON course_archives(status, academic_year, semester)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_tasks_archive
            ON batch_tasks(course_archive_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lesson_plans_archive
            ON lesson_plans(course_archive_id)
        """)

        # AI usage and generated-content quality observability.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_usage_metrics (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                operation TEXT DEFAULT 'generate',
                status TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                cached_input_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                estimated_cost REAL DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS content_quality_metrics (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                score REAL NOT NULL,
                dimensions TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._add_column_if_not_exists(
            db, "ai_usage_metrics", "cached_input_tokens", "INTEGER DEFAULT 0"
        )
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_usage_created
            ON ai_usage_metrics(created_at, provider, model)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality_source
            ON content_quality_metrics(source_type, source_id, created_at)
        """)

        # ====================================================================
        # Competition module tables (教学能力比赛模块)
        # ====================================================================

        # Competition projects table - shared cover info between lesson plan & report
        await db.execute("""
            CREATE TABLE IF NOT EXISTS competition_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                competition_year TEXT,
                competition_region TEXT,
                competition_level TEXT,
                work_name TEXT,
                course_name TEXT,
                major_category TEXT,
                major_name TEXT,
                group_name TEXT,
                total_hours INTEGER DEFAULT 16,
                hours_per_lesson INTEGER DEFAULT 2,
                class_name TEXT,
                location TEXT,
                textbook_info TEXT,
                context_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Competition outputs table - each project may produce multiple lesson plans/reports
        await db.execute("""
            CREATE TABLE IF NOT EXISTS competition_outputs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                output_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                generated_data TEXT,
                output_file_path TEXT,
                progress_current INTEGER DEFAULT 0,
                progress_total INTEGER DEFAULT 0,
                error_message TEXT,
                related_lesson_plan_id TEXT,
                topics_input TEXT,
                additional_requirements TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (project_id) REFERENCES competition_projects(id)
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_comp_outputs_project
            ON competition_outputs(project_id, output_type)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_comp_outputs_status
            ON competition_outputs(status)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_comp_projects_created
            ON competition_projects(created_at)
        """)

    async def _add_column_if_not_exists(
        self,
        db: aiosqlite.Connection,
        table_name: str,
        column_name: str,
        column_type: str
    ) -> None:
        """Add a column to a table if it doesn't exist."""
        # Check if column exists
        cursor = await db.execute(f"PRAGMA table_info({table_name})")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        if column_name not in column_names:
            await db.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get a database connection."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            yield db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Yield one connection and commit or roll back all statements atomically."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            try:
                await db.execute("BEGIN")
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def execute(
        self,
        sql: str,
        parameters: tuple = (),
        commit: bool = False,
    ) -> aiosqlite.Cursor:
        """Execute a SQL query."""
        async with self.get_connection() as db:
            cursor = await db.execute(sql, parameters)
            if commit:
                await db.commit()
            return cursor

    async def fetch_one(
        self,
        sql: str,
        parameters: tuple = (),
    ) -> Optional[sqlite3.Row]:
        """Fetch a single row."""
        async with self.get_connection() as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(sql, parameters)
            row = await cursor.fetchone()
            return row

    async def fetch_all(
        self,
        sql: str,
        parameters: tuple = (),
    ) -> list[sqlite3.Row]:
        """Fetch all rows."""
        async with self.get_connection() as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(sql, parameters)
            rows = await cursor.fetchall()
            return rows


# Global database instance
db = Database(settings.database_path)


async def get_db() -> Database:
    """Get the database instance."""
    return db


async def init_db() -> None:
    """Initialize the database."""
    await db.initialize()
