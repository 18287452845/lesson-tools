import json

import pytest

from backend.services import chapter_splitter as chapter_splitter_module
from backend.services.chapter_splitter import (
    ChapterSplitter,
    _extract_stream_content,
)


@pytest.mark.unit
def test_extract_stream_content_ignores_nullable_and_metadata_chunks():
    assert (
        _extract_stream_content(
            {
                "choices": [
                    {
                        "delta": {
                            "role": "assistant",
                            "content": None,
                        }
                    }
                ]
            }
        )
        == ""
    )
    assert _extract_stream_content({"choices": [{"delta": {"content": "OK"}}]}) == "OK"
    assert _extract_stream_content({"delta": {"text": "OK"}}) == "OK"
    assert _extract_stream_content({"delta": {"text": None}}) == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chapter_stream_skips_null_content_chunks(monkeypatch):
    chapter_payload = [
        {
            "lesson_number": 1,
            "topic": "Test topic",
            "content_summary": "Test summary",
            "key_concepts": ["concept"],
        }
    ]

    class FakeProvider:
        async def generate_stream(self, prompt, system_prompt=None):
            yield (
                "data: "
                + json.dumps(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "role": "assistant",
                                    "content": None,
                                }
                            }
                        ]
                    }
                )
            )
            yield (
                "data: "
                + json.dumps(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "content": json.dumps(chapter_payload),
                                }
                            }
                        ]
                    }
                )
            )
            yield "data: [DONE]"

    monkeypatch.setattr(
        chapter_splitter_module.AIProviderFactory,
        "create_provider",
        staticmethod(lambda *args, **kwargs: FakeProvider()),
    )

    splitter = ChapterSplitter(
        provider="deepseek",
        api_key="test-key",
        model="deepseek-v4-flash",
    )
    chapters = [
        chapter
        async for chapter in splitter._generate_ai_chapters_stream(
            course_name="Test course",
            subject="Test subject",
            grade="Test grade",
            total_hours=2,
            hours_per_lesson=2,
            num_lessons=1,
        )
    ]

    assert len(chapters) == 1
    assert chapters[0].lesson_number == 1
    assert chapters[0].topic == "Test topic"
