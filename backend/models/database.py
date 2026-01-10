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

        # Add batch-related columns to lesson_plans if they don't exist
        await self._add_column_if_not_exists(
            db, "lesson_plans", "batch_task_id", "TEXT"
        )
        await self._add_column_if_not_exists(
            db, "lesson_plans", "lesson_number", "INTEGER"
        )

        # Add hours-based columns to batch_tasks if upgrading from week-based
        await self._add_column_if_not_exists(
            db, "batch_tasks", "total_hours", "INTEGER"
        )
        await self._add_column_if_not_exists(
            db, "batch_tasks", "hours_per_lesson", "INTEGER DEFAULT 2"
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

        # Add class_ids to lesson_plans
        await self._add_column_if_not_exists(
            db, "lesson_plans", "class_ids", "TEXT"
        )

        # Add task_type to batch_tasks (for draft vs normal tasks)
        await self._add_column_if_not_exists(
            db, "batch_tasks", "task_type", "TEXT DEFAULT 'normal'"
        )

        # Create indexes for lesson plan draft management
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lesson_plans_status_template
            ON lesson_plans(status, template_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_tasks_type_status
            ON batch_tasks(task_type, status)
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
            yield db

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
