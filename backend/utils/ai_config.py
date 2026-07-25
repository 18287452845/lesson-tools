"""
Utility functions for getting user-configured AI settings from database
"""
from typing import Optional
from ..models.database import db
from ..config import normalize_deepseek_model, settings


async def get_user_ai_config() -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get user-configured AI provider, API key, and model from database.

    Returns:
        Tuple of (provider, api_key, model)
    """
    row = await db.fetch_one(
        "SELECT value FROM user_settings WHERE key = ?",
        ("ai_provider_config",),
    )

    if row:
        import json
        config = json.loads(row["value"])
        provider = config.get("provider")
        api_key = config.get("api_key")
        model = config.get("model")

        if provider and api_key:
            if provider == "deepseek" and model:
                model = normalize_deepseek_model(model)
            return provider, api_key, model

    # Fallback to environment settings
    provider = settings.ai_provider
    api_key = settings.get_active_api_key()
    model = settings.get_active_model()

    return provider, api_key, model


async def get_ai_generator():
    """Get an AI generator instance with user configuration."""
    from ..services.ai_generator import AIGenerator

    provider, api_key, model = await get_user_ai_config()

    return AIGenerator(
        provider=provider,
        api_key=api_key,
        model=model,
    )


async def get_ai_editor():
    """Get an AI editor instance with user configuration."""
    from ..services.ai_editor import AIEditor

    provider, api_key, model = await get_user_ai_config()

    return AIEditor(
        provider=provider,
        api_key=api_key,
        model=model,
    )
