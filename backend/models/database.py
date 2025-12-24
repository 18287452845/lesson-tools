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
