"""Utilities for loading and applying user-configured AI settings."""
import json
import logging
from typing import Optional

from ..models.database import db
from ..config import normalize_deepseek_model, settings


logger = logging.getLogger(__name__)


def resolve_ai_model(provider: str, model: Optional[str] = None) -> str:
    """Resolve a provider-specific model into a stable value for persistence."""
    if provider == "deepseek":
        return normalize_deepseek_model(model or settings.deepseek_model)
    if provider == "anthropic":
        return model or settings.anthropic_model
    raise ValueError(f"Unsupported AI provider: {provider}")


def apply_runtime_ai_config(provider: str, api_key: str, model: Optional[str]) -> None:
    """Apply one validated AI configuration without logging its credential."""
    selected_model = resolve_ai_model(provider, model)
    if provider == "deepseek":
        settings.deepseek_api_key = api_key
        settings.deepseek_model = selected_model
    elif provider == "anthropic":
        settings.anthropic_api_key = api_key
        settings.anthropic_model = selected_model

    settings.ai_provider = provider
    settings.ai_model = selected_model


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
        try:
            config = json.loads(row["value"])
            provider = config.get("provider")
            api_key = config.get("api_key")
            model = config.get("model")
            if provider not in {"deepseek", "anthropic"} or not api_key:
                raise ValueError("provider or credential is missing")
            if provider == "deepseek" and model:
                model = normalize_deepseek_model(model)
            return provider, api_key, resolve_ai_model(provider, model)
        except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
            logger.warning(
                "Persisted AI configuration is invalid; falling back to environment settings"
            )

    # Fallback to environment settings
    provider = settings.ai_provider
    api_key = settings.get_active_api_key()
    model = settings.get_active_model()

    return provider, api_key, model


async def restore_runtime_ai_config() -> bool:
    """Restore the database-preferred AI configuration after process startup."""
    provider, api_key, model = await get_user_ai_config()
    if not provider or not api_key:
        return False
    apply_runtime_ai_config(provider, api_key, model)
    return True


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
