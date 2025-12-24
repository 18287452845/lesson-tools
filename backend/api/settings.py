"""
Settings API endpoints for managing AI provider configuration.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models.database import db
from ..config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


class AIProviderConfig(BaseModel):
    """AI Provider Configuration"""
    provider: str = Field(..., description="AI提供商: 'deepseek' 或 'anthropic'")
    api_key: str = Field(..., description="API密钥")
    model: Optional[str] = Field(None, description="模型名称（可选）")


class AIProviderResponse(BaseModel):
    """AI Provider Response"""
    provider: str
    model: str
    configured: bool
    has_api_key: bool


@router.get("/ai-provider", response_model=AIProviderResponse)
async def get_ai_provider_config():
    """
    获取当前AI提供商配置
    """
    # 检查是否配置了API密钥
    has_deepseek_key = bool(settings.deepseek_api_key)
    has_anthropic_key = bool(settings.anthropic_api_key)

    current_provider = settings.ai_provider
    current_model = settings.get_active_model()

    # 检查当前提供商是否有API密钥
    if current_provider == "deepseek":
        has_key = has_deepseek_key
    else:
        has_key = has_anthropic_key

    return AIProviderResponse(
        provider=current_provider,
        model=current_model,
        configured=has_key,
        has_api_key=has_key,
    )


@router.post("/ai-provider")
async def set_ai_provider_config(config: AIProviderConfig):
    """
    设置AI提供商配置（运行时，不持久化）
    注意：此API仅在运行时生效，重启后需要重新配置
    建议在环境变量或.env文件中配置
    """
    # 验证提供商
    if config.provider not in ["deepseek", "anthropic"]:
        raise HTTPException(
            status_code=400,
            detail="不支持的AI提供商，请选择 'deepseek' 或 'anthropic'"
        )

    # 保存到数据库（user_settings表）
    import json

    config_value = json.dumps({
        "provider": config.provider,
        "api_key": config.api_key,
        "model": config.model,
    })

    await db.execute(
        """
        INSERT OR REPLACE INTO user_settings (key, value, updated_at)
        VALUES ('ai_provider_config', ?, CURRENT_TIMESTAMP)
        """,
        (config_value,),
        commit=True,
    )

    # 更新运行时配置
    settings.ai_provider = config.provider
    if config.provider == "deepseek":
        settings.deepseek_api_key = config.api_key
        if config.model:
            settings.deepseek_model = config.model
    else:
        settings.anthropic_api_key = config.api_key
        if config.model:
            settings.anthropic_model = config.model

    if config.model:
        settings.ai_model = config.model

    return {
        "message": "AI提供商配置已更新",
        "provider": config.provider,
        "model": config.model or settings.get_active_model(),
    }


@router.get("/ai-providers")
async def list_ai_providers():
    """
    获取可用的AI提供商列表
    """
    return {
        "providers": [
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "description": "DeepSeek AI - 高性能中文AI模型",
                "models": [
                    {"id": "deepseek-chat", "name": "DeepSeek Chat"},
                    {"id": "deepseek-coder", "name": "DeepSeek Coder"},
                ],
                "default_model": "deepseek-chat",
                "website": "https://www.deepseek.com/",
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "description": "Anthropic Claude - 高质量AI助手",
                "models": [
                    {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
                    {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
                    {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
                ],
                "default_model": "claude-sonnet-4-20250514",
                "website": "https://www.anthropic.com/",
            },
        ]
    }


@router.get("/app-info")
async def get_app_info():
    """
    获取应用信息
    """
    return {
        "name": "智能教案助手",
        "version": "1.0.0",
        "default_provider": settings.ai_provider,
        "default_model": settings.get_active_model(),
    }
