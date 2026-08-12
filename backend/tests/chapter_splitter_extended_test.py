"""Extended behavior coverage for chapter splitting and streaming allocation."""

import json
import types

import pytest

from backend.services import chapter_splitter as splitter_module


def _chapter(number, topic, summary="", concepts=None, experiment_name=None):
    return splitter_module.ChapterInfo(
        lesson_number=number,
        topic=topic,
        content_summary=summary,
        key_concepts=concepts or [],
        experiment_name=experiment_name,
    )


def _chapter_dict(number, topic):
    return {
        "lesson_number": number,
        "topic": topic,
        "content_summary": f"{topic}概述",
        "key_concepts": ["概念", "嵌套", "3"],
        "experiment_name": "实验" if number % 2 else "",
    }


def test_chapter_normalization_helpers_cover_expand_merge_and_defaults():
    assert splitter_module._flatten_key_concepts("not-list") == []
    assert splitter_module._flatten_key_concepts(["A", ["B", ["C"]], 4]) == [
        "A",
        "B",
        "C",
        "4",
    ]
    assert splitter_module._dedupe_preserve_order(["A", "B", "A"]) == ["A", "B"]
    assert splitter_module._build_additional_info_section("  实践优先  ").endswith("实践优先")
    assert splitter_module._build_additional_info_section(" ") == ""
    assert splitter_module._build_chapters_reference_section(None) == ""
    assert splitter_module._build_chapters_reference_section("\n\n") == ""
    reference = splitter_module._build_chapters_reference_section("第一章\n\n 第二章 ")
    assert "- 第一章" in reference and "- 第二章" in reference

    source = [
        _chapter(7, "", "概述一", ["A", "B"]),
        _chapter(9, "第二课", "概述二", ["B", "C"]),
        _chapter(10, "第三课", "概述三", ["D"]),
    ]
    exact = splitter_module._normalize_chapters_to_count(source[:2], 2)
    assert [item.lesson_number for item in exact] == [1, 2]
    assert exact[0].topic == "第1课"

    expanded = splitter_module._normalize_chapters_to_count(source[:2], 5)
    assert len(expanded) == 5
    assert expanded[0].topic == "第1课"
    assert expanded[3].topic.endswith("(1/2)")

    merged = splitter_module._normalize_chapters_to_count(source, 2)
    assert len(merged) == 2
    assert merged[0].key_concepts == ["A", "B", "C"]
    assert "概述一" in merged[0].content_summary

    assert splitter_module._normalize_chapters_to_count(source, 0) == []
    assert splitter_module._normalize_chapters_to_count([], 2) == []
    assert len(splitter_module.normalize_chapters_for_hours(source, 4, 2)) == 2


def test_manual_partial_and_json_parsing_variants():
    splitter = splitter_module.ChapterSplitter("deepseek", "key", "model")
    manual = splitter._parse_manual_chapters(" 第一章 \n\n第二章")
    assert [item.topic for item in manual] == ["第一章", "第二章"]

    fenced = splitter._parse_json_response("```json\n[{\"topic\": \"A\"}]\n```")
    assert fenced == [{"topic": "A"}]
    generic_fence = splitter._parse_json_response("```\n[{\"topic\": \"B\"}]\n```")
    assert generic_fence[0]["topic"] == "B"
    fixed = splitter._parse_json_response('[{"topic":"C",}]')
    assert fixed[0]["topic"] == "C"
    with pytest.raises(ValueError, match="JSON array"):
        splitter._parse_json_response('{"topic":"not-array"}')
    with pytest.raises(ValueError, match="Failed to parse"):
        splitter._parse_json_response("not-json")

    nested = _chapter_dict(1, "第一课")
    nested["key_concepts"] = ["概念", ["嵌套"], 3]
    partial = splitter._try_parse_partial_chapters(
        json.dumps([nested], ensure_ascii=False)
    )
    assert partial[0].key_concepts == ["概念", "嵌套", "3"]
    assert splitter._try_parse_partial_chapters("no array") == []
    assert splitter._try_parse_partial_chapters("[broken]") == []


@pytest.mark.service
async def test_ai_chapter_generation_batches_and_validates(monkeypatch):
    calls = []

    async def generate_with_ai(**kwargs):
        calls.append(kwargs["prompt"])
        count = 12 if len(calls) == 1 else 2
        return json.dumps(
            [
                {
                    "topic": f"第{index}课",
                    "key_concepts": ["A", ["B"]],
                    "experiment_name": "实验" if index % 2 else "",
                }
                for index in range(1, count + 1)
            ],
            ensure_ascii=False,
        )

    monkeypatch.setattr(splitter_module, "generate_with_ai", generate_with_ai)
    splitter = splitter_module.ChapterSplitter("deepseek", "key", "model")
    chapters = await splitter._generate_ai_chapters(
        "Python",
        "软件技术",
        "大一",
        28,
        2,
        14,
        "第一章\n第二章",
        "增加实践",
    )
    assert len(chapters) == 14
    assert chapters[-1].lesson_number == 14
    assert chapters[0].content_summary == ""
    assert chapters[0].key_concepts == ["A", "B"]
    assert "第13-14课" in calls[1]

    async def invalid_ai(**kwargs):
        return '[{"content_summary":"missing topic"}]'

    monkeypatch.setattr(splitter_module, "generate_with_ai", invalid_ai)
    with pytest.raises(ValueError, match="Failed to parse chapter"):
        await splitter._generate_ai_chapters("X", "Y", "Z", 2, 2, 1)


@pytest.mark.service
async def test_split_course_validates_count_and_experiment_names(monkeypatch):
    splitter = splitter_module.ChapterSplitter("deepseek", "key", "model")

    async def generated(*args, **kwargs):
        return [
            _chapter(1, "第一课", experiment_name="实验一"),
            _chapter(2, "第二课", experiment_name=""),
        ]

    normalized_calls = []

    async def ensure_names(chapters, **kwargs):
        normalized_calls.append(kwargs)
        return [item.model_dump() for item in chapters], False

    monkeypatch.setattr(splitter, "_generate_ai_chapters", generated)
    monkeypatch.setattr(splitter_module, "ensure_experiment_names", ensure_names)
    result = await splitter.split_course_chapters("Python", "软件", "大一", 4, 2)
    assert len(result) == 2
    assert normalized_calls[0]["require_every_group"] is True

    async def wrong_count(*args, **kwargs):
        return [_chapter(1, "只有一课")]

    monkeypatch.setattr(splitter, "_generate_ai_chapters", wrong_count)
    with pytest.raises(ValueError, match="数量不匹配"):
        await splitter.split_course_chapters("Python", "软件", "大一", 4, 2)

    async def fake_split(self, *args, **kwargs):
        return [_chapter(1, "便捷函数")]

    monkeypatch.setattr(splitter_module.ChapterSplitter, "split_course_chapters", fake_split)
    convenience = await splitter_module.split_course_chapters("Python", "软件", "大一", 2)
    assert convenience[0].topic == "便捷函数"


@pytest.mark.service
async def test_chapter_streaming_parses_sse_and_batch_local_numbers(monkeypatch):
    payload = json.dumps(
        [_chapter_dict(1, "第一课"), _chapter_dict(2, "第二课")],
        ensure_ascii=False,
    )

    async def generate_stream(*args, **kwargs):
        yield "ignored"
        yield "data: not-json"
        yield "data: " + json.dumps({"choices": [{"delta": {"content": payload}}]})
        yield "data: [DONE]"

    provider = types.SimpleNamespace(generate_stream=generate_stream)
    monkeypatch.setattr(
        splitter_module.AIProviderFactory,
        "create_provider",
        lambda *args: provider,
    )
    splitter = splitter_module.ChapterSplitter()
    chapters = [
        item
        async for item in splitter._generate_ai_chapters_stream(
            "Python", "软件", "大一", 4, 2, 2, "章节", "说明"
        )
    ]
    assert [item.lesson_number for item in chapters] == [1, 2]


@pytest.mark.service
async def test_smart_allocation_retry_fill_truncate_and_stream_fallback(monkeypatch):
    splitter = splitter_module.ChapterSplitter("deepseek", "key", "model")
    prompt = splitter._build_smart_allocation_prompt(
        "Python",
        "软件",
        "大一",
        "第一章\n第二章",
        5,
        4,
        20,
        "实践优先",
    )
    assert "1. 第一章" in prompt and "实践优先" in prompt

    responses = [
        json.dumps([_chapter_dict(1, "一")]),
        json.dumps([_chapter_dict(i, f"第{i}周") for i in range(1, 6)]),
    ]

    async def generate(*args, **kwargs):
        return responses.pop(0)

    provider = types.SimpleNamespace(generate=generate)
    monkeypatch.setattr(
        splitter_module.AIProviderFactory,
        "create_provider",
        lambda *args: provider,
    )

    async def no_sleep(*args):
        return None

    monkeypatch.setattr(splitter_module.asyncio, "sleep", no_sleep)
    retried = await splitter._generate_smart_allocation(
        "Python", "软件", "大一", "第一章", 5, 4, 20
    )
    assert len(retried) == 5

    provider.generate = lambda *args, **kwargs: None

    async def four_of_five(*args, **kwargs):
        return json.dumps([_chapter_dict(i, f"第{i}周") for i in (1, 2, 4, 5)])

    provider.generate = four_of_five
    filled = await splitter._generate_smart_allocation(
        "Python", "软件", "大一", "第一章", 5, 4, 20
    )
    assert [item.lesson_number for item in filled] == [1, 2, 3, 4, 5]
    assert filled[2].topic.endswith("待补充")

    async def too_many(*args, **kwargs):
        return json.dumps([_chapter_dict(i, f"第{i}周") for i in range(1, 7)])

    provider.generate = too_many
    truncated = await splitter._generate_smart_allocation(
        "Python", "软件", "大一", "第一章", 5, 4, 20
    )
    assert len(truncated) == 5

    async def sync_weeks(*args, **kwargs):
        return [_chapter(1, "第1周"), _chapter(2, "第2周")]

    monkeypatch.setattr(splitter, "_generate_smart_allocation", sync_weeks)
    non_stream_provider = types.SimpleNamespace(generate=generate)
    monkeypatch.setattr(
        splitter_module.AIProviderFactory,
        "create_provider",
        lambda *args: non_stream_provider,
    )
    streamed = [
        item
        async for item in splitter._generate_smart_allocation_stream(
            "Python", "软件", "大一", "第一章", 2, 4, 8
        )
    ]
    assert [item.lesson_number for item in streamed] == [1, 2]
