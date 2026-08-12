"""Extended tests for dynamic AI lesson generation and response recovery."""

import json

import pytest

from backend.services import ai_generator as generator_module


def _input():
    return generator_module.LessonPlanInput(
        template_id="yunlin-standard",
        subject="Python",
        grade="大一",
        topic="列表操作",
        duration="2课时",
        textbook_name="Python 基础",
        unit_name="数据结构",
        location="实训楼",
        prior_knowledge="掌握变量",
        additional_requirements="突出实践",
    )


def _valid_content():
    long_knowledge_teacher = "讲解核心原理、演示操作步骤、分析典型错误并指导结果验证。" * 8
    long_knowledge_student = "观察演示、记录要点、同步操作并逐项核对运行结果。" * 7
    long_practice_teacher = "发布实践任务、说明操作步骤、巡回指导排错并检查验收证据。" * 6
    long_practice_student = "独立完成配置、记录错误现象、定位原因、修复问题、验证结果并提交证据。" * 8
    return {
        "teaching_goals": {
            "knowledge": ["理解列表"],
            "ability": ["操作列表"],
            "quality": ["严谨编码"],
        },
        "teaching_steps": [
            {
                "stage": "新课预热",
                "duration": "1分钟",
                "teacher_activity": "准备案例",
                "student_activity": "准备环境",
                "design_intent": "衔接旧知",
            },
            {
                "stage": "问题导入",
                "duration": "1分钟",
                "teacher_activity": "提出问题",
                "student_activity": "思考问题",
                "design_intent": "激发兴趣",
            },
            {
                "stage": "探究新知",
                "duration": "1分钟",
                "teacher_activity": long_knowledge_teacher,
                "student_activity": long_knowledge_student,
                "design_intent": "掌握原理",
            },
            {
                "stage": "巩固练习",
                "duration": "1分钟",
                "teacher_activity": long_practice_teacher,
                "student_activity": long_practice_student,
                "design_intent": "形成技能",
            },
            {
                "stage": "课堂小结",
                "duration": "1分钟",
                "teacher_activity": "总结重点",
                "student_activity": "复述要点",
                "design_intent": "巩固知识",
            },
        ],
    }


@pytest.mark.service
async def test_generation_retries_sparse_output_then_normalizes_valid_steps(monkeypatch):
    generator = generator_module.AIGenerator("deepseek", "key", "model")
    responses = [
        json.dumps(
            {
                "teaching_steps": [
                    {
                        "stage": "讲授新课",
                        "teacher_activity": "太短",
                        "student_activity": "太短",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        json.dumps(_valid_content(), ensure_ascii=False),
    ]
    prompts = []

    async def generate_with_ai(**kwargs):
        prompts.append(kwargs["prompt"])
        assert kwargs["response_format"] == {"type": "json_object"}
        return responses.pop(0)

    async def no_sleep(*args):
        return None

    monkeypatch.setattr(generator_module, "generate_with_ai", generate_with_ai)
    monkeypatch.setattr(generator_module.asyncio, "sleep", no_sleep)
    result = await generator.generate_lesson_plan(_input(), generate_reflection=True)
    assert len(result.teaching_steps) == 5
    assert result.teaching_steps[0].stage == "新课预热"
    assert result.teaching_steps[2].duration == "30分钟"
    assert result.teaching_steps[2].teacher_activity.startswith("【教师】")
    assert "上一次输出未达到" in prompts[1]


@pytest.mark.service
async def test_generation_and_field_convenience_methods(monkeypatch):
    calls = []

    async def generate_with_ai(**kwargs):
        calls.append(kwargs)
        return "field result"

    monkeypatch.setattr(generator_module, "generate_with_ai", generate_with_ai)
    generator = generator_module.AIGenerator("deepseek", "key", "model")
    current = {
        "teaching_goals": {
            "knowledge": ["知识"],
            "ability": ["能力"],
            "quality": ["素质"],
        }
    }

    for field_name in ("teaching_steps", "teaching_goals", "homework", "other"):
        value = await generator.regenerate_field(
            _input(), field_name, current, "结合岗位"
        )
        assert value == "field result"
    for optimization in ("detailed", "concise", "professional", "engaging", "other"):
        value = await generator.optimize_field(
            _input(), "key_points", "原内容", optimization
        )
        assert value == "field result"

    async def fake_generate(self, input_data, field_configs=None, generate_reflection=False):
        return generator_module.GeneratedContent(key_points="便捷生成")

    monkeypatch.setattr(generator_module.AIGenerator, "generate_lesson_plan", fake_generate)
    generated = await generator_module.generate_lesson_plan(
        _input(), "deepseek", "key", "model", generate_reflection=True
    )
    assert generated.key_points == "便捷生成"


def test_dynamic_templates_notes_required_fields_and_hint_inference():
    generator = generator_module.AIGenerator()
    fields = [
        generator_module.FieldConfig(
            name="teaching_goals", display_name="教学目标", field_type="json"
        ),
        generator_module.FieldConfig(
            name="reflection", display_name="教学反思", field_type="textarea"
        ),
        generator_module.FieldConfig(
            name="teaching_steps",
            display_name="教学过程",
            field_type="array",
            description="五阶段",
        ),
        generator_module.FieldConfig(
            name="homework", display_name="作业", field_type="json"
        ),
        generator_module.FieldConfig(
            name="custom_process", display_name="自定义流程", field_type="json"
        ),
        generator_module.FieldConfig(
            name="learner_analysis", display_name="学习者分析", field_type="textarea"
        ),
        generator_module.FieldConfig(
            name="teacher_name", display_name="教师", field_type="text", required=False
        ),
    ]
    template = generator._build_dynamic_json_template(fields, generate_reflection=True)
    assert '"teaching_goals"' in template
    assert '"reflection"' in template
    assert '"custom_process"' in template
    assert "成功之处" in template

    notes = generator._build_field_generation_notes(fields, generate_reflection=True)
    assert "自定义字段说明" in notes
    assert "custom_process" in notes
    required = generator._build_required_fields_note(fields)
    assert "五阶段" in required
    assert "共 **6** 个必填字段" in required
    assert generator._build_required_fields_note([]) == ""
    optional_only = [
        generator_module.FieldConfig(
            name="optional", display_name="可选", required=False
        )
    ]
    assert generator._build_required_fields_note(optional_only) == ""

    prompt = generator._build_generation_prompt(_input(), fields, True)
    assert "Python 基础" in prompt
    assert "实训楼" in prompt
    default_input = generator_module.LessonPlanInput(
        template_id="yunlin-standard",
        subject="Python",
        grade="大一",
        topic="函数",
        duration="2课时",
    )
    default_prompt = generator._build_generation_prompt(default_input)
    assert "无特殊说明" in default_prompt
    assert "待课后填写" in default_prompt

    cases = {
        "course_name": "名称",
        "plan_date": "日期",
        "school": "学校",
        "teacher": "教师",
        "class_name": "名称",
        "classroom": "教室",
        "student_analysis": "分析",
        "course_description": "描述",
        "learning_goals": "目标",
        "work_steps": "流程",
        "safety_checklist": "清单",
        "teacher_notes": "教师",
        "course_notes": "备注",
        "learning_resources": "资源",
        "unknown": "unknown",
    }
    for name, expected in cases.items():
        assert expected in generator._infer_field_hint(name)


def test_field_prompts_json_parsing_sanitizing_and_validation_errors():
    generator = generator_module.AIGenerator()
    input_data = _input()
    emotion_context = {
        "teaching_goals": {
            "knowledge": ["知识"],
            "ability": ["能力"],
            "emotion": ["情感"],
        }
    }
    assert "情感态度价值观" in generator._build_field_prompt(
        input_data, "key_points", emotion_context, None
    )
    assert "教学步骤数组" in generator._build_field_prompt(
        input_data, "teaching_steps", {}, None
    )
    assert "knowledge" in generator._build_field_prompt(
        input_data, "teaching_goals", {}, None
    )
    assert "required" in generator._build_field_prompt(
        input_data, "homework", {}, None
    )

    fenced = generator._parse_json_response("```json\n{\"key_points\":\"重点\"}\n```")
    assert fenced["key_points"] == "重点"
    generic = generator._parse_json_response("```\n{\"key_points\":\"重点2\"}\n```")
    assert generic["key_points"] == "重点2"
    embedded = generator._parse_json_response(
        '说明文字 {"key_points":"包含 } 和 \\\" 引号"} 尾部'
    )
    assert embedded["key_points"].startswith("包含")
    trailing = generator._parse_json_response('{"key_points":"重点",}')
    assert trailing["key_points"] == "重点"
    unquoted = generator._parse_json_response('{key_points: "重点"}')
    assert unquoted["key_points"] == "重点"
    with pytest.raises(ValueError, match="Failed to parse"):
        generator._parse_json_response("not-json")

    dirty = {"text": "a\x00b", "items": ["c\x07d"], "number": 3}
    assert generator._sanitize_control_chars(dirty) == {
        "text": "ab",
        "items": ["cd"],
        "number": 3,
    }
    assert generator._clean_ai_response("") == ""
    assert generator._clean_ai_response("\ufeffa\x00b") == "ab"

    with pytest.raises(ValueError, match="teaching_steps缺失"):
        generator._validate_teaching_step_detail({})
    with pytest.raises(ValueError, match="缺少教学阶段"):
        generator._validate_teaching_step_detail(
            {"teaching_steps": [{"stage": "新课预热"}]}
        )
    sparse = _valid_content()
    sparse["teaching_steps"][2]["teacher_activity"] = "短"
    generator._normalize_teaching_steps(sparse)
    with pytest.raises(ValueError, match="传授新知教师活动"):
        generator._validate_teaching_step_detail(sparse)

    untouched = {"teaching_steps": "not-list"}
    generator._normalize_teaching_steps(untouched)
    assert untouched["teaching_steps"] == "not-list"
    generator._normalize_teaching_steps({"teaching_steps": ["not-dict"]})
