import pytest

from backend.api.settings import list_ai_providers
from backend.config import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    DEEPSEEK_MODELS,
    normalize_deepseek_model,
    settings,
)
from backend.services import ai_provider


@pytest.mark.unit
def test_deepseek_defaults_and_legacy_model_mapping():
    assert DEEPSEEK_BASE_URL == "https://api.deepseek.com"
    assert DEEPSEEK_DEFAULT_MODEL == "deepseek-v4-flash"
    assert DEEPSEEK_MODELS == ("deepseek-v4-flash", "deepseek-v4-pro")
    assert normalize_deepseek_model("deepseek-chat") == DEEPSEEK_DEFAULT_MODEL
    assert normalize_deepseek_model("deepseek-coder") == DEEPSEEK_DEFAULT_MODEL
    assert normalize_deepseek_model("deepseek-v4-pro") == "deepseek-v4-pro"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deepseek_provider_uses_latest_chat_endpoint_and_token_limit(monkeypatch):
    request = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            request["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, **kwargs):
            request["url"] = url
            request["post_kwargs"] = kwargs
            return FakeResponse()

    monkeypatch.setattr(settings, "deepseek_base_url", f"{DEEPSEEK_BASE_URL}/")
    monkeypatch.setattr(ai_provider.httpx, "AsyncClient", FakeAsyncClient)

    provider = ai_provider.DeepSeekProvider(
        api_key="test-key",
        model="deepseek-chat",
        max_tokens=16384,
    )
    result = await provider.generate("hello")

    assert result == "ok"
    assert provider.model == DEEPSEEK_DEFAULT_MODEL
    assert request["url"] == "https://api.deepseek.com/chat/completions"
    assert request["post_kwargs"]["json"]["max_tokens"] == 16384

    unlimited_provider = ai_provider.DeepSeekProvider(
        api_key="test-key",
        model="deepseek-v4-flash",
        max_tokens=0,
    )
    await unlimited_provider.generate("hello")

    assert "max_tokens" not in request["post_kwargs"]["json"]

    anthropic_provider = ai_provider.AnthropicProvider(
        api_key="test-key",
        max_tokens=0,
    )
    assert anthropic_provider.max_tokens == 4096


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deepseek_models_are_exposed_by_settings_api():
    response = await list_ai_providers()
    deepseek = next(
        provider for provider in response["providers"] if provider["id"] == "deepseek"
    )

    assert deepseek["default_model"] == DEEPSEEK_DEFAULT_MODEL
    assert tuple(model["id"] for model in deepseek["models"]) == DEEPSEEK_MODELS
