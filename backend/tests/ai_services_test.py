"""Tests for AI provider plumbing, retries, and editor prompt behavior."""

import httpx
import pytest

from backend.services import ai_editor
from backend.services import ai_provider
from backend.utils import ai_config


@pytest.mark.service
async def test_retry_with_backoff_success_exhaustion_and_non_retryable(monkeypatch):
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    monkeypatch.setattr(ai_provider.asyncio, "sleep", fake_sleep)
    attempts = 0

    async def eventually_succeeds():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.ReadError("temporary")
        return "ok"

    result = await ai_provider.retry_with_backoff(
        eventually_succeeds,
        max_retries=3,
        initial_delay=0.5,
        backoff_multiplier=2,
    )
    assert result == "ok"
    assert sleeps == [0.5, 1.0]

    async def always_fails():
        raise httpx.ConnectError("offline")

    with pytest.raises(httpx.ConnectError):
        await ai_provider.retry_with_backoff(
            always_fails,
            max_retries=1,
            initial_delay=0.1,
            backoff_multiplier=2,
        )

    async def invalid_request():
        raise ValueError("do not retry")

    with pytest.raises(ValueError, match="do not retry"):
        await ai_provider.retry_with_backoff(invalid_request, max_retries=3)


def _fake_http_client(response, captured):
    class Client:
        def __init__(self, *args, **kwargs):
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            captured["url"] = url
            captured["request"] = kwargs
            return response

    return Client


@pytest.mark.service
async def test_deepseek_and_anthropic_generate_payloads_and_errors(monkeypatch):
    captured = {}
    success = httpx.Response(
        200,
        request=httpx.Request("POST", "https://example.test"),
        json={"choices": [{"message": {"content": "DeepSeek result"}}]},
    )
    monkeypatch.setattr(
        ai_provider.httpx,
        "AsyncClient",
        _fake_http_client(success, captured),
    )
    deepseek = ai_provider.DeepSeekProvider("key", "deepseek-chat", max_tokens=123)
    result = await deepseek.generate(
        "user prompt",
        "system prompt",
        response_format={"type": "json_object"},
    )
    assert result == "DeepSeek result"
    payload = captured["request"]["json"]
    assert payload["messages"][0]["role"] == "system"
    assert payload["max_tokens"] == 123
    assert payload["response_format"] == {"type": "json_object"}
    assert deepseek._parse_response(success.json()) == "DeepSeek result"
    with pytest.raises(ValueError, match="Invalid DeepSeek"):
        deepseek._parse_response({})

    bad_request = httpx.Response(
        400,
        request=httpx.Request("POST", "https://example.test"),
        text="bad key",
    )
    monkeypatch.setattr(
        ai_provider.httpx,
        "AsyncClient",
        _fake_http_client(bad_request, {}),
    )
    with pytest.raises(ValueError, match="status 400"):
        await deepseek.generate("prompt")

    anthropic_response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://example.test"),
        json={"content": [{"text": "Claude result"}]},
    )
    anthropic_capture = {}
    monkeypatch.setattr(
        ai_provider.httpx,
        "AsyncClient",
        _fake_http_client(anthropic_response, anthropic_capture),
    )
    anthropic = ai_provider.AnthropicProvider("key", max_tokens=0)
    assert anthropic.max_tokens == 4096
    assert await anthropic.generate("prompt", "system") == "Claude result"
    assert anthropic_capture["request"]["json"]["system"] == "system"
    with pytest.raises(ValueError, match="Invalid Anthropic"):
        anthropic._parse_response({"content": []})

    anthropic_bad = httpx.Response(
        401,
        request=httpx.Request("POST", "https://example.test"),
        text="unauthorized",
    )
    monkeypatch.setattr(
        ai_provider.httpx,
        "AsyncClient",
        _fake_http_client(anthropic_bad, {}),
    )
    with pytest.raises(ValueError, match="status 401"):
        await anthropic.generate("prompt")


def _fake_stream_client(status_code, lines, body=b"error"):
    class StreamResponse:
        def __init__(self):
            self.status_code = status_code
            self.request = httpx.Request("POST", "https://example.test")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def aread(self):
            return body

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "error",
                    request=self.request,
                    response=httpx.Response(self.status_code, request=self.request),
                )

        async def aiter_lines(self):
            for line in lines:
                yield line

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, *args, **kwargs):
            return StreamResponse()

    return Client


@pytest.mark.service
async def test_provider_streaming_success_and_error_wrapping(monkeypatch):
    monkeypatch.setattr(
        ai_provider.httpx,
        "AsyncClient",
        _fake_stream_client(200, ["", "data: one", "data: two"]),
    )
    deepseek = ai_provider.DeepSeekProvider("key")
    assert [line async for line in deepseek.generate_stream("p", "s")] == [
        "data: one",
        "data: two",
    ]

    monkeypatch.setattr(
        ai_provider.httpx,
        "AsyncClient",
        _fake_stream_client(200, ["event: start", "data: text"]),
    )
    anthropic = ai_provider.AnthropicProvider("key")
    assert [line async for line in anthropic.generate_stream("p", "s")] == [
        "event: start",
        "data: text",
    ]

    monkeypatch.setattr(
        ai_provider.httpx,
        "AsyncClient",
        _fake_stream_client(503, [], b"unavailable"),
    )
    with pytest.raises(Exception, match="AI生成失败"):
        [line async for line in deepseek.generate_stream("p")]
    with pytest.raises(Exception, match="AI生成失败"):
        [line async for line in anthropic.generate_stream("p")]


@pytest.mark.service
async def test_provider_factory_and_convenience_generation(monkeypatch):
    monkeypatch.setattr(ai_provider.settings, "deepseek_api_key", None)
    monkeypatch.setattr(ai_provider.settings, "ai_provider", "deepseek")
    with pytest.raises(ValueError, match="API密钥"):
        ai_provider.AIProviderFactory.create_provider()

    deepseek = ai_provider.AIProviderFactory.create_provider(
        "deepseek", "key", "deepseek-chat", 99
    )
    anthropic = ai_provider.AIProviderFactory.create_provider(
        "anthropic", "key", "claude-test", 88
    )
    assert isinstance(deepseek, ai_provider.DeepSeekProvider)
    assert isinstance(anthropic, ai_provider.AnthropicProvider)
    with pytest.raises(ValueError, match="不支持"):
        ai_provider.AIProviderFactory.create_provider("other", "key", "model")

    calls = []

    async def generate(prompt, system_prompt, response_format=None):
        calls.append((prompt, system_prompt, response_format))
        return "generated"

    monkeypatch.setattr(
        ai_provider.AIProviderFactory,
        "create_provider",
        lambda *args: type("Provider", (), {"generate": staticmethod(generate)})(),
    )
    result = await ai_provider.generate_with_ai(
        "prompt",
        "system",
        response_format={"type": "json_object"},
    )
    assert result == "generated"
    assert calls[0][2] == {"type": "json_object"}


@pytest.mark.service
async def test_ai_editor_methods_and_prompt_branches(monkeypatch):
    calls = []

    async def fake_generate(**kwargs):
        calls.append(kwargs)
        return "AI content"

    monkeypatch.setattr(ai_editor, "generate_with_ai", fake_generate)
    editor = ai_editor.AIEditor("deepseek", "key", "model")
    context = {
        "subject": "Python",
        "grade": "大一",
        "topic": "列表",
        "teaching_goals": {
            "knowledge": ["理解列表"],
            "ability": ["操作列表"],
            "emotion": ["严谨编码"],
        },
        "key_points": "索引",
        "difficult_points": "切片",
        "teaching_process": "过程" * 300,
    }

    assert await editor.generate_reflection(context) == "AI content"
    assert "..." in calls[-1]["prompt"]
    assert await editor.modify_content("原内容", "更具体", context, "key_points") == "AI content"
    assert "教学重点" in calls[-1]["prompt"]
    await editor.modify_content("原内容", "优化", context, "teaching_process")
    assert "教学过程" in calls[-1]["prompt"]
    await editor.modify_content("原内容", "重写", context, None)
    assert "上下文信息" in calls[-1]["prompt"]

    for enhancement in ("detailed", "professional", "simplified", "rewrite", "other"):
        assert (
            await editor.enhance_content(
                "内容", enhancement, context, "保留示例" if enhancement == "detailed" else None
            )
            == "AI content"
        )

    for section in ("reflection", "blackboard_design", "teaching_process", "homework"):
        assert (
            await editor.generate_missing_section(section, context, "联系实际")
            == "AI content"
        )
    assert await editor.append_to_section("原内容", "增加案例", context) == "AI content"

    string_goals = {**context, "teaching_goals": "掌握列表", "teaching_process": "短过程"}
    assert "掌握列表" in editor._build_reflection_prompt(string_goals)
    non_dict_reflection = editor._build_missing_section_prompt(
        "reflection", string_goals, None
    )
    assert "掌握列表" in non_dict_reflection

    assert await ai_editor.generate_reflection(context, "deepseek", "key") == "AI content"
    assert (
        await ai_editor.modify_content(
            "原内容", "修改", context, "key_points", "deepseek", "key"
        )
        == "AI content"
    )


@pytest.mark.service
async def test_user_ai_config_database_and_factory_helpers(test_db, monkeypatch):
    monkeypatch.setattr(ai_config, "db", test_db)
    await test_db.execute(
        "INSERT INTO user_settings (key, value) VALUES (?, ?)",
        (
            "ai_provider_config",
            '{"provider":"deepseek","api_key":"db-key","model":"deepseek-chat"}',
        ),
        commit=True,
    )
    provider, key, model = await ai_config.get_user_ai_config()
    assert (provider, key, model) == ("deepseek", "db-key", "deepseek-v4-flash")

    created = []

    def fake_generator(**kwargs):
        created.append(("generator", kwargs))
        return kwargs

    def fake_editor(**kwargs):
        created.append(("editor", kwargs))
        return kwargs

    monkeypatch.setattr("backend.services.ai_generator.AIGenerator", fake_generator)
    monkeypatch.setattr("backend.services.ai_editor.AIEditor", fake_editor)
    assert (await ai_config.get_ai_generator())["api_key"] == "db-key"
    assert (await ai_config.get_ai_editor())["model"] == "deepseek-v4-flash"

    await test_db.execute(
        "DELETE FROM user_settings WHERE key = ?",
        ("ai_provider_config",),
        commit=True,
    )
    monkeypatch.setattr(ai_config.settings, "ai_provider", "anthropic")
    monkeypatch.setattr(ai_config.settings, "anthropic_api_key", "env-key")
    monkeypatch.setattr(ai_config.settings, "anthropic_model", "claude-env")
    monkeypatch.setattr(ai_config.settings, "ai_model", None)
    assert await ai_config.get_user_ai_config() == (
        "anthropic",
        "env-key",
        "claude-env",
    )
