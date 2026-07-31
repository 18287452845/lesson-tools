import json

import pytest

from backend.models.schemas import GeneratedContent, LessonPlanInput
from backend.services import ai_generator as ai_generator_module
from backend.services.ai_generator import AIGenerator


def _detailed_teaching_steps():
    return [
        {
            "stage": "新课预热",
            "duration": "5分钟",
            "teacher_activity": "【教师】展示案例并组织复习。",
            "student_activity": "【学生】观察案例并回顾旧知。",
            "design_intent": "完成知识衔接。",
        },
        {
            "stage": "问题导入",
            "duration": "5分钟",
            "teacher_activity": "【教师】提出任务问题并明确学习目标。",
            "student_activity": "【学生】分析问题并提出初步方案。",
            "design_intent": "形成任务驱动。",
        },
        {
            "stage": "传授新知",
            "duration": "30分钟",
            "teacher_activity": "【教师】" + "讲解核心原理、演示配置步骤、分析典型错误并说明验证方法；" * 8,
            "student_activity": "【学生】" + "依据任务单观察演示、记录参数、回答问题并同步核对结果；" * 7,
            "design_intent": "建立原理、操作和验证证据之间的联系。",
        },
        {
            "stage": "课堂实践",
            "duration": "30分钟",
            "teacher_activity": "【教师】" + "发布分层任务、明确验收标准、巡视指导并提示排错方法；" * 7,
            "student_activity": "【学生】" + "完成配置、排查故障、验证结果、保存证据、互评并根据反馈改进；" * 9,
            "design_intent": "形成岗位实践和质量验收能力。",
        },
        {
            "stage": "课堂总结",
            "duration": "5分钟",
            "teacher_activity": "【教师】归纳知识、操作与验收要点。",
            "student_activity": "【学生】复盘任务并完成自评。",
            "design_intent": "形成完整认知。",
        },
    ]


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
        return json.dumps(
            {
                "key_points": "A key point",
                "teaching_steps": _detailed_teaching_steps(),
            }
        )

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


def test_teaching_step_normalization_and_sparse_content_rejection():
    data = {"teaching_steps": _detailed_teaching_steps()}
    data["teaching_steps"][2]["stage"] = "探究新知"
    data["teaching_steps"][3]["stage"] = "巩固练习"
    data["teaching_steps"][2]["duration"] = "20分钟"

    AIGenerator._normalize_teaching_steps(data)
    AIGenerator._validate_teaching_step_detail(data)

    assert data["teaching_steps"][2]["stage"] == "传授新知"
    assert data["teaching_steps"][2]["duration"] == "30分钟"
    assert data["teaching_steps"][3]["stage"] == "课堂实践"

    data["teaching_steps"][2]["teacher_activity"] = "【教师】简单讲解。"
    with pytest.raises(ValueError, match="传授新知教师活动"):
        AIGenerator._validate_teaching_step_detail(data)


def test_generation_prompt_requires_dense_fixed_core_stages():
    generator = AIGenerator()
    prompt = generator._build_generation_prompt(
        LessonPlanInput(
            template_id="yunlin-standard",
            subject="信息安全技术",
            grade="24级",
            topic="Windows本地安全策略配置",
            duration="2课时",
        )
    )

    assert '第3阶段："传授新知"（讲授核心内容，固定30分钟）' in prompt
    assert '第4阶段："课堂实践"（实践操作、练习巩固，固定30分钟）' in prompt
    assert "传授新知”教师活动不少于120个汉字" in prompt
    assert "“课堂实践”教师活动不少于80个汉字、学生活动不少于120个汉字" in prompt
