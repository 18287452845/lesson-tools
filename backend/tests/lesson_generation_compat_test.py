import json

import pytest

from backend.models.schemas import GeneratedContent, LessonPlanInput
from backend.services import ai_generator as ai_generator_module
from backend.services.ai_generator import AIGenerator


@pytest.mark.unit
def test_generated_content_normalizes_ai_text_lists():
    content = GeneratedContent(
        reflection=["First observation", "Second observation"],
        online_resources=["Resource A", "Resource B"],
        key_points=["Point A", "Point B"],
    )

    assert content.reflection == "First observation\nSecond observation"
    assert content.online_resources == "Resource A\nResource B"
    assert content.key_points == "Point A\nPoint B"


@pytest.mark.unit
def test_generated_content_has_optional_online_resources():
    content = GeneratedContent(key_points="A key point")

    assert content.online_resources is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lesson_generator_requests_deepseek_json_output(monkeypatch):
    request = {}

    async def fake_generate_with_ai(**kwargs):
        request.update(kwargs)
        return json.dumps({"key_points": "A key point"})

    monkeypatch.setattr(
        ai_generator_module,
        "generate_with_ai",
        fake_generate_with_ai,
    )

    generator = AIGenerator(
        provider="deepseek",
        api_key="test-key",
        model="deepseek-v4-flash",
    )
    result = await generator.generate_lesson_plan(
        LessonPlanInput(
            template_id="test-template",
            subject="Test subject",
            grade="Test grade",
            topic="Test topic",
            duration="2 hours",
        )
    )

    assert result.key_points == "A key point"
    assert request["response_format"] == {"type": "json_object"}
