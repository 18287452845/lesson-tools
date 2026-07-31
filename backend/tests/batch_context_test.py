import json

import pydantic
import pytest

from backend.api import batch
from backend.models import schemas
from backend.services.batch_context import (
    build_class_names,
    build_class_names_from_selections,
    format_class_names,
    join_display_values,
    validate_experiment_schedule_coverage,
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
    names = build_class_names_from_selections(
        "2025级",
        [
            ("大数据技术", [1, 2, 3]),
            ("云计算技术应用", [2, 3]),
        ],
    )

    assert format_class_names(names) == (
        "2025级大数据技术1、2、3班，2025级云计算技术应用2、3班"
    )
    assert "2025级云计算技术应用1班" not in names
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
        major_classes=[
            {"major": " 大数据技术 ", "class_numbers": [1, 2, 3]},
            {"major": "云计算技术应用", "class_numbers": [2, 3, 3]},
        ],
        locations=["慧心楼3516", " 实训楼204 "],
        supplemental_artifacts=["experiment_plan"],
        academic_year="2025-2026",
        semester=2,
        teacher_name="李阳",
        plan_date="2026-02-25",
        first_class_date="2026-03-05",
        class_periods="3-4",
    )

    assert request.major_classes[0].major == "大数据技术"
    assert request.major_classes[0].class_numbers == [1, 2, 3]
    assert request.major_classes[1].class_numbers == [2, 3]
    assert request.locations == ["慧心楼3516", "实训楼204"]


def test_experiment_plan_accepts_one_schedule_per_class_without_legacy_fields():
    request = schemas.BatchTaskCreateRequest(
        course_name="Windows服务器安全配置",
        subject="信息安全技术应用",
        grade="2024级",
        template_id="yunlin-standard",
        total_hours=4,
        chapters=_chapters(),
        major_classes=[
            {"major": "信息安全技术应用", "class_numbers": [1, 2]},
        ],
        supplemental_artifacts=["experiment_plan"],
        academic_year="2025-2026",
        semester=2,
        teacher_name="李阳",
        plan_date="2026-02-25",
        experiment_schedules=[
            {
                "class_name": "2024级信息安全技术应用1班",
                "weekday": 4,
                "class_periods": "3-4",
                "first_class_date": "2026-03-05",
                "classroom": "慧心楼3516",
            },
            {
                "class_name": "2024级信息安全技术应用2班",
                "weekday": 5,
                "class_periods": "5-6",
                "first_class_date": "2026-03-06",
                "classroom": "实训楼204",
            },
        ],
    )

    assert request.location is None
    assert request.first_class_date is None
    assert request.class_periods is None
    assert [item.classroom for item in request.experiment_schedules] == [
        "慧心楼3516",
        "实训楼204",
    ]


def test_experiment_schedule_rejects_date_that_does_not_match_weekday():
    with pytest.raises(pydantic.ValidationError, match="第一周日期必须是星期四"):
        schemas.ExperimentClassSchedule(
            class_name="2024级信息安全技术应用1班",
            weekday=4,
            class_periods="3-4",
            first_class_date="2026-03-06",
            classroom="慧心楼3516",
        )


def test_experiment_schedule_coverage_requires_exactly_one_entry_per_class():
    classes = ["2024级信息安全技术应用1班", "2024级信息安全技术应用2班"]
    exact = [
        {"class_name": classes[0]},
        {"class_name": classes[1]},
    ]

    validate_experiment_schedule_coverage(classes, exact)

    with pytest.raises(ValueError, match="缺少"):
        validate_experiment_schedule_coverage(classes, exact[:1])
    with pytest.raises(ValueError, match="每个班级只能配置一条实验课安排"):
        validate_experiment_schedule_coverage(classes, [exact[0], exact[0]])


def test_per_major_selection_rejects_out_of_range_class_number():
    with pytest.raises(pydantic.ValidationError, match="班级只能选择 1-5 班"):
        schemas.BatchTaskCreateRequest(
            course_name="网络安全",
            subject="云计算技术应用",
            grade="2024级",
            template_id="yunlin-standard",
            total_hours=4,
            chapters=_chapters(),
            major_classes=[{"major": "云计算技术应用", "class_numbers": [2, 6]}],
        )


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
async def test_create_batch_task_persists_per_major_class_numbers(monkeypatch):
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
        major_classes=[
            {"major": "大数据技术", "class_numbers": [1, 2, 3]},
            {"major": "云计算技术应用", "class_numbers": [2, 3]},
        ],
        locations=["慧心楼3516", "实训楼204"],
        supplemental_artifacts=["experiment_plan"],
        academic_year="2025-2026",
        semester=2,
        teacher_name="李阳",
        plan_date="2026-02-25",
        experiment_schedules=[
            {
                "class_name": class_name,
                "weekday": 4,
                "class_periods": "3-4",
                "first_class_date": "2026-03-05",
                "classroom": f"实验室{index}",
            }
            for index, class_name in enumerate(
                [
                    "2024级大数据技术1班",
                    "2024级大数据技术2班",
                    "2024级大数据技术3班",
                    "2024级云计算技术应用2班",
                    "2024级云计算技术应用3班",
                ],
                start=1,
            )
        ],
    )

    response = await batch.create_batch_task(request)
    params = captured["params"]

    assert response.status == "pending"
    assert params[2] == "大数据技术，云计算技术应用"
    assert params[10] == "慧心楼3516，实训楼204"
    assert params[14] == (
        "2024级大数据技术1班,2024级大数据技术2班,2024级大数据技术3班,"
        "2024级云计算技术应用2班,2024级云计算技术应用3班"
    )
    assert "2024级云计算技术应用1班" not in params[14]
    persisted_schedules = json.loads(params[22])
    assert [item["class_name"] for item in persisted_schedules] == [
        "2024级大数据技术1班",
        "2024级大数据技术2班",
        "2024级大数据技术3班",
        "2024级云计算技术应用2班",
        "2024级云计算技术应用3班",
    ]
    assert [item["classroom"] for item in persisted_schedules] == [
        "实验室1",
        "实验室2",
        "实验室3",
        "实验室4",
        "实验室5",
    ]


@pytest.mark.asyncio
async def test_batch_task_table_contains_experiment_schedules_column(test_db):
    async with test_db.get_connection() as connection:
        cursor = await connection.execute("PRAGMA table_info(batch_tasks)")
        columns = [row[1] for row in await cursor.fetchall()]

    assert "experiment_schedules" in columns
