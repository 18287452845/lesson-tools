"""
Configuration management for the lesson plan tool.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # API Keys - 支持多种AI提供商
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")

    # AI Provider Configuration
    ai_provider: str = os.getenv("AI_PROVIDER", "deepseek")  # 'anthropic' 或 'deepseek'
    ai_model: Optional[str] = os.getenv("AI_MODEL")  # 如果不设置则使用默认值

    # DeepSeek Configuration
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"  # 默认模型

    # Anthropic Configuration
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    storage_dir: Path = base_dir / "storage"
    template_dir: Path = storage_dir / "templates"
    upload_dir: Path = storage_dir / "uploads"
    output_dir: Path = storage_dir / "outputs"
    database_path: str = str(storage_dir / "database.db")

    # AI Settings
    ai_max_tokens: int = 4096
    ai_temperature: float = 0.7

    def get_active_model(self) -> str:
        """获取当前激活的AI模型"""
        if self.ai_model:
            return self.ai_model
        if self.ai_provider == "deepseek":
            return self.deepseek_model
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
