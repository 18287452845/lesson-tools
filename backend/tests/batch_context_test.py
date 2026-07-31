import pydantic
import pytest

from backend.api import batch
from backend.models import schemas
from backend.services.batch_context import (
    build_class_names,
    format_class_names,
    join_display_values,
)


def _chapters():
    return [
        schemas.ChapterInfo(
            lesson_number=index,
            topic=f"任务{index}",
            content_summary="完成任务并验证结果",
            key_concepts=["配置", "验证"],
        )
        for index in (1, 2)
    ]


def test_build_and_format_single_major_classes():
    names = build_class_names(
        "2024级",
        ["信息安全技术应用"],
        [1, 2, 2, 5],
    )

    assert names == [
        "2024级信息安全技术应用1班",
        "2024级信息安全技术应用2班",
        "2024级信息安全技术应用5班",
    ]
    assert format_class_names(names) == "2024级信息安全技术应用1、2、5班"


def test_format_multiple_majors_and_locations_with_chinese_commas():
    names = build_class_names(
        "2025级",
        ["信息安全技术应用", "计算机网络技术"],
        [1, 2],
    )

    assert format_class_names(names) == (
        "2025级信息安全技术应用1、2班，2025级计算机网络技术1、2班"
    )
    assert join_display_values([" 慧心楼3516 ", "实训楼204", "慧心楼3516"]) == (
        "慧心楼3516，实训楼204"
    )


def test_structured_batch_request_accepts_new_selection_fields():
    request = schemas.BatchTaskCreateRequest(
        course_name="Windows服务器安全配置",
        subject="信息安全技术应用，计算机网络技术",
        grade="2024级",
        template_id="yunlin-standard",
        total_hours=4,
        chapters=_chapters(),
        majors=[" 信息安全技术应用 ", "计算机网络技术"],
        class_numbers=[1, 2, 2],
        locations=["慧心楼3516", " 实训楼204 "],
        supplemental_artifacts=["experiment_plan"],
        academic_year="2025-2026",
        semester=2,
        teacher_name="李阳",
        plan_date="2026-02-25",
        first_class_date="2026-03-05",
        class_periods="3-4",
    )

    assert request.majors == ["信息安全技术应用", "计算机网络技术"]
    assert request.class_numbers == [1, 2]
    assert request.locations == ["慧心楼3516", "实训楼204"]


@pytest.mark.parametrize(
    ("grade", "class_numbers", "message"),
    [
        ("2021级", [1], "年级必须为 2022级 至 2035级"),
        ("2036级", [1], "年级必须为 2022级 至 2035级"),
        ("2024级", [6], "班级只能选择 1-5 班"),
    ],
)
def test_structured_batch_request_rejects_out_of_range_values(
    grade: str,
    class_numbers: list[int],
    message: str,
):
    with pytest.raises(pydantic.ValidationError, match=message):
        schemas.BatchTaskCreateRequest(
            course_name="网络安全",
            subject="信息安全技术应用",
            grade=grade,
            template_id="yunlin-standard",
            total_hours=4,
            chapters=_chapters(),
            majors=["信息安全技术应用"],
            class_numbers=class_numbers,
        )


@pytest.mark.asyncio
async def test_create_batch_task_persists_normalized_professional_context(monkeypatch):
    captured: dict[str, tuple] = {}

    class FakeDatabase:
        async def execute(self, _sql, params, commit=False):
            assert commit is True
            captured["params"] = params

    async def fake_get_db():
        return FakeDatabase()

    class FakeProcessor:
        async def process_batch_task(self, _task_id):
            return None

    def fake_background(coroutine, **_kwargs):
        coroutine.close()

    monkeypatch.setattr(batch, "get_db", fake_get_db)
    monkeypatch.setattr(batch, "require_valid_builtin_template", lambda _template_id: None)
    monkeypatch.setattr(batch, "BatchTaskProcessor", lambda **_kwargs: FakeProcessor())
    monkeypatch.setattr(batch, "run_in_background", fake_background)

    request = schemas.BatchTaskCreateRequest(
        course_name="Windows服务器安全配置",
        subject="旧值",
        grade="2024级",
        template_id="yunlin-standard",
        total_hours=4,
        chapters=_chapters(),
        majors=["信息安全技术应用", "计算机网络技术"],
        class_numbers=[1, 2],
        locations=["慧心楼3516", "实训楼204"],
    )

    response = await batch.create_batch_task(request)
    params = captured["params"]

    assert response.status == "pending"
    assert params[2] == "信息安全技术应用，计算机网络技术"
    assert params[10] == "慧心楼3516，实训楼204"
    assert params[14] == (
        "2024级信息安全技术应用1班,2024级信息安全技术应用2班,"
        "2024级计算机网络技术1班,2024级计算机网络技术2班"
    )
