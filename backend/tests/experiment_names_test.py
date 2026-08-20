import json

import pytest

from backend.services import experiment_names
from backend.services import batch_processor as batch_processor_module
from backend.services import chapter_splitter as chapter_splitter_module


def _chapters():
    return [
        {
            "lesson_number": index,
            "topic": f"Python教学主题{index}",
            "content_summary": "",
            "key_concepts": [],
            "experiment_name": "",
        }
        for index in range(1, 5)
    ]


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("Python环境配置\n与验证", "不能包含换行"),
        ("Python环境配置…", "不能包含省略号"),
        ("Python环境配置...", "不能包含省略号"),
        ("一二三四五六七八九十一二三四五六七八九", "不能超过 18 个字符"),
    ],
)
def test_experiment_name_validation_rejects_wrapping_and_ellipsis(name, message):
    with pytest.raises(ValueError, match=message):
        experiment_names.validate_experiment_name(name)


def test_merged_experiment_name_is_validated_before_rendering():
    chapters = _chapters()[:2]
    chapters[0]["experiment_name"] = "Python环境配置测试"
    chapters[1]["experiment_name"] = "虚拟环境依赖管理"

    with pytest.raises(ValueError, match="不能超过 18 个字符"):
        experiment_names.validate_experiment_chapters(
            chapters,
            require_every_group=False,
        )


@pytest.mark.asyncio
async def test_invalid_generated_names_are_regenerated_until_compliant(monkeypatch):
    responses = iter(
        [
            json.dumps(
                [
                    {"group_number": 1, "experiment_name": "名称过长名称过长名称过长名称过长名称过长"},
                    {"group_number": 2, "experiment_name": "函数实验"},
                ],
                ensure_ascii=False,
            ),
            json.dumps(
                [
                    {"group_number": 1, "experiment_name": "Python环境配置"},
                    {"group_number": 2, "experiment_name": "函数模块应用"},
                ],
                ensure_ascii=False,
            ),
        ]
    )
    calls = []

    async def fake_generate_with_ai(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(experiment_names, "generate_with_ai", fake_generate_with_ai)

    result, regenerated = await experiment_names.ensure_experiment_names(
        _chapters(),
        provider="deepseek",
        api_key="test-key",
        model="deepseek-v4",
        require_every_group=True,
    )

    assert regenerated is True
    assert len(calls) == 2
    assert [chapter["experiment_name"] for chapter in result] == [
        "Python环境配置",
        "",
        "函数模块应用",
        "",
    ]
    assert "最多 18 个字符" in calls[0]["prompt"]


def test_chapter_generation_prompt_requires_short_experiment_names():
    prompt = chapter_splitter_module.ChapterSplitter.CHAPTER_SPLIT_PROMPT

    assert '"experiment_name"' in prompt
    assert "experiment_name最多18个字符" in prompt
    assert "不得包含换行" in prompt
    assert "不得包含" in prompt and "省略号" in prompt


@pytest.mark.asyncio
async def test_batch_merge_revalidates_regenerates_and_persists_names(
    monkeypatch,
    tmp_path,
):
    corrected = _chapters()[:2]
    corrected[0]["experiment_name"] = "Python环境配置"
    captured = {}

    async def fake_ensure(chapters, **kwargs):
        captured["input_chapters"] = chapters
        captured["ensure_kwargs"] = kwargs
        return corrected, True

    class FakeDatabase:
        async def execute(self, sql, params, commit=False):
            captured["sql"] = sql
            captured["params"] = params
            captured["commit"] = commit

        async def fetch_all(self, sql, params=()):
            content = json.dumps(
                {
                    "teaching_goals": {"knowledge": ["目标"]},
                    "key_points": "教学重点内容",
                    "difficult_points": "教学难点内容",
                    "teaching_steps": [
                        {
                            "stage": "课堂实践",
                            "teacher_activity": "组织Python环境配置实验",
                            "student_activity": "完成Python环境配置实验",
                            "design_intent": "实践",
                        }
                    ],
                    "homework": {"required": "练习"},
                },
                ensure_ascii=False,
            )
            return [
                {
                    "lesson_number": number,
                    "topic": f"Python教学主题{number}",
                    "generated_content": content,
                    "final_content": None,
                }
                for number in (1, 2)
            ]

    async def fake_get_db():
        return FakeDatabase()

    class FakeRenderer:
        def render_experiment_plans(self, **kwargs):
            captured["render_kwargs"] = kwargs
            return [str(tmp_path / "experiment.docx")]

    monkeypatch.setattr(batch_processor_module, "ensure_experiment_names", fake_ensure)
    monkeypatch.setattr(batch_processor_module, "get_db", fake_get_db)

    processor_class = batch_processor_module.BatchTaskProcessor
    processor = processor_class.__new__(processor_class)
    processor.provider = "deepseek"
    processor.api_key = "test-key"
    processor.model = "deepseek-v4"
    processor.hours_per_lesson = 2
    processor.course_plan_renderer = FakeRenderer()

    files = await processor._generate_course_plan_files(
        batch_task_id="batch-merge",
        task={
            "supplemental_artifacts": json.dumps(["experiment_plan"]),
            "class_names": "2024级信息安全技术应用1班",
            "course_name": "Python编程基础",
            "grade": "2024级",
            "academic_year": "2026-2027",
            "semester": 1,
            "teacher_name": "李阳",
            "hours_per_lesson": 2,
            "start_week": 1,
            "location": "慧心楼3713",
            "plan_date": "2026-08-01",
            "first_class_date": "2026-09-03",
            "class_periods": "5-6",
            "experiment_schedules": "[]",
        },
        chapters=_chapters()[:2],
    )

    assert captured["ensure_kwargs"]["require_every_group"] is False
    assert [
        chapter["experiment_name"]
        for chapter in captured["render_kwargs"]["chapters"]
    ] == ["Python环境配置", ""]
    assert "UPDATE batch_tasks SET chapters" in captured["sql"]
    assert json.loads(captured["params"][0])[0]["experiment_name"] == "Python环境配置"
    assert captured["commit"] is True
    assert files[0]["topics"] == ["课程实验计划表"]
