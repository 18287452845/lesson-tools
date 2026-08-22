"""Tests for AI focus/difficulty condensation."""

import pytest

from backend.services import point_briefs as module
from backend.services.point_briefs import ensure_brief_points


def _chapter(number, key_points, difficult_points):
    return {
        "lesson_number": number,
        "topic": f"课题{number}",
        "key_points": key_points,
        "difficult_points": difficult_points,
    }


@pytest.mark.service
async def test_all_compliant_chapters_skip_ai(monkeypatch):
    async def fail_ai(**kwargs):
        raise AssertionError("不应触发 AI 调用")

    monkeypatch.setattr(module, "generate_with_ai", fail_ai)
    chapters = [
        _chapter(1, "掌握列表索引", "理解切片边界"),
        _chapter(2, "掌握字典操作", "区分键与值"),
    ]

    result, regenerated = await ensure_brief_points(
        chapters, provider=None, api_key=None, model=None
    )

    assert result == chapters
    assert regenerated is False


@pytest.mark.service
async def test_only_non_compliant_chapters_are_sent(monkeypatch):
    prompts = []

    async def fake_ai(**kwargs):
        prompts.append(kwargs["prompt"])
        return '[{"lesson_number": 2, "key_points": "掌握异常处理", "difficult_points": "理解传播机制"}]'

    monkeypatch.setattr(module, "generate_with_ai", fake_ai)
    chapters = [
        _chapter(1, "掌握列表索引", "理解切片边界"),
        _chapter(2, "掌握raise语句主动抛出异常的方法；掌握assert断言的语法与适用场景", "区分场景"),
    ]

    result, regenerated = await ensure_brief_points(
        chapters, provider=None, api_key=None, model=None
    )

    assert regenerated is True
    assert len(prompts) == 1
    assert "掌握列表索引" not in prompts[0]  # 合规教案不进入提示词
    assert "assert断言" in prompts[0]
    assert result[0]["key_points"] == "掌握列表索引"  # 合规教案保持原样
    assert result[1]["key_points"] == "掌握异常处理"
    assert result[1]["difficult_points"] == "理解传播机制"


@pytest.mark.service
async def test_mismatched_results_fail_after_retries(monkeypatch):
    calls = []

    async def fake_ai(**kwargs):
        calls.append(1)
        return "[]"  # 数量不一致，必然失败

    monkeypatch.setattr(module, "generate_with_ai", fake_ai)
    chapters = [_chapter(1, "掌握" + "很" * 30 + "长", "难点")]

    with pytest.raises(ValueError, match="重难点精简连续"):
        await ensure_brief_points(chapters, provider=None, api_key=None, model=None)
    assert len(calls) == module.POINT_BRIEF_GENERATION_ATTEMPTS
