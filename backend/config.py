"""
Configuration management for the lesson plan tool.
"""
import os
from pathlib import Path
from typing import ClassVar, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"
DEEPSEEK_MODELS = ("deepseek-v4-flash", "deepseek-v4-pro")
DEEPSEEK_LEGACY_MODELS = {
    "deepseek-chat": DEEPSEEK_DEFAULT_MODEL,
    "deepseek-reasoner": DEEPSEEK_DEFAULT_MODEL,
    "deepseek-coder": DEEPSEEK_DEFAULT_MODEL,
}


def normalize_deepseek_model(model: str) -> str:
    """Map retired DeepSeek model names to the current default model."""
    return DEEPSEEK_LEGACY_MODELS.get(model, model)


class Settings(BaseSettings):
    """Application settings."""

    # API Keys - 支持多种AI提供商
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")

    # AI Provider Configuration
    ai_provider: str = os.getenv("AI_PROVIDER", "deepseek")  # 'anthropic' 或 'deepseek'
    ai_model: Optional[str] = os.getenv("AI_MODEL")  # 如果不设置则使用默认值

    # DeepSeek Configuration
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", DEEPSEEK_BASE_URL)
    deepseek_model: str = DEEPSEEK_DEFAULT_MODEL

    # Anthropic Configuration
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    storage_dir: Path = base_dir / "storage"
    builtin_template_path: ClassVar[Path] = (
        base_dir / "backend" / "resources" / "templates" / "yunlin_lesson_plan.docx"
    )
    teaching_plan_template_path: ClassVar[Path] = (
        base_dir / "backend" / "resources" / "templates" / "yunlin_teaching_plan.docx"
    )
    experiment_plan_template_path: ClassVar[Path] = (
        base_dir / "backend" / "resources" / "templates" / "yunlin_experiment_plan.docx"
    )
    upload_dir: Path = storage_dir / "uploads"
    output_dir: Path = storage_dir / "outputs"
    database_path: str = ""
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "")

    # External book discovery services
    google_books_api_key: Optional[str] = os.getenv("GOOGLE_BOOKS_API_KEY")
    google_books_base_url: str = os.getenv(
        "GOOGLE_BOOKS_BASE_URL", "https://www.googleapis.com/books/v1"
    )
    open_library_base_url: str = os.getenv(
        "OPEN_LIBRARY_BASE_URL", "https://openlibrary.org"
    )
    tsinghua_press_base_url: str = os.getenv(
        "TSINGHUA_PRESS_BASE_URL", "https://www.tup.tsinghua.edu.cn"
    )
    book_search_timeout: float = float(os.getenv("BOOK_SEARCH_TIMEOUT", "15.0"))
    book_search_max_results: int = int(os.getenv("BOOK_SEARCH_MAX_RESULTS", "8"))
    book_search_user_agent: str = os.getenv(
        "BOOK_SEARCH_USER_AGENT",
        "YunlinLessonTools/1.1 (educational textbook discovery)",
    )

    # AI Settings
    # 0 means "do not send max_tokens"; DeepSeek then applies the model/API limit.
    ai_max_tokens: int = int(os.getenv("AI_MAX_TOKENS", "0"))
    ai_max_tokens_batch: int = int(os.getenv("AI_MAX_TOKENS_BATCH", "0"))
    ai_temperature: float = 0.7
    ai_timeout: float = float(os.getenv("AI_TIMEOUT", "180.0"))  # AI 请求超时（秒）

    # AI Retry Settings
    ai_max_retries: int = int(os.getenv("AI_MAX_RETRIES", "2"))  # 最大重试次数（2次重试=3次尝试）
    ai_retry_delay: float = float(os.getenv("AI_RETRY_DELAY", "1.0"))  # 重试延迟（秒）
    ai_retry_backoff: float = float(os.getenv("AI_RETRY_BACKOFF", "2.0"))  # 指数退避倍数

    # Batch Processing Concurrency Settings
    batch_max_concurrent_documents: int = int(os.getenv("BATCH_MAX_CONCURRENT_DOCUMENTS", "5"))  # Maximum documents to generate concurrently
    batch_max_concurrent_lessons: int = int(os.getenv("BATCH_MAX_CONCURRENT_LESSONS", "10"))  # Maximum lesson plans to generate concurrently
    batch_connection_pool_size: int = int(os.getenv("BATCH_CONNECTION_POOL_SIZE", "50"))  # HTTP connection pool size
    batch_connection_keepalive: float = float(os.getenv("BATCH_CONNECTION_KEEPALIVE", "30.0"))  # HTTP connection keepalive timeout (seconds)

    def get_active_model(self) -> str:
        """获取当前激活的AI模型"""
        if self.ai_model:
            if self.ai_provider == "deepseek":
                return normalize_deepseek_model(self.ai_model)
            return self.ai_model
        if self.ai_provider == "deepseek":
            return normalize_deepseek_model(self.deepseek_model)
        return self.anthropic_model

    def get_active_api_key(self) -> Optional[str]:
        """获取当前激活的API密钥"""
        if self.ai_provider == "deepseek":
            return self.deepseek_api_key
        return self.anthropic_api_key

    # API Settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_prefix: str = "/api"

    # File Upload Settings
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: set = {".docx"}

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.database_path = self._resolve_database_path()
        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_database_path(self) -> str:
        database_url = os.getenv("DATABASE_URL")
        if database_url and database_url.startswith("sqlite"):
            if database_url.startswith("sqlite:///"):
                raw_path = database_url[len("sqlite:///"):]
            elif database_url.startswith("sqlite://"):
                raw_path = database_url[len("sqlite://"):]
            else:
                raw_path = ""

            if raw_path:
                return self._normalize_path(raw_path)

        database_path = os.getenv("DATABASE_PATH")
        if database_path:
            return self._normalize_path(database_path)

        return str(self.storage_dir / "database.db")

    def _normalize_path(self, raw_path: str) -> str:
        path = Path(raw_path.strip())
        if path.is_absolute():
            return str(path)
        return str((self.base_dir / path).resolve())


# Global settings instance
settings = Settings()
