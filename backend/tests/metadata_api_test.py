"""Integration tests for class, subject, and grade management APIs."""

import datetime

import pytest

from backend.api import classes as classes_api
from backend.api import grades as grades_api
from backend.api import subjects as subjects_api


@pytest.mark.api
async def test_class_crud_and_not_found_paths(test_client, test_db, monkeypatch):
    monkeypatch.setattr(classes_api, "db", test_db)

    invalid = await test_client.post("/api/classes", json={"name": ""})
    assert invalid.status_code == 422

    first = await test_client.post(
        "/api/classes",
        json={"name": "网络安全 1 班", "description": "主校区"},
    )
    second = await test_client.post(
        "/api/classes",
        json={"name": "网络安全 2 班"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    first_id = first.json()["id"]

    listed = await test_client.get("/api/classes", params={"page": 2, "limit": 1})
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert len(listed.json()["classes"]) == 1

    fetched = await test_client.get(f"/api/classes/{first_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "网络安全 1 班"

    updated = await test_client.put(
        f"/api/classes/{first_id}",
        json={"name": "网络安全 3 班", "description": "实训楼"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "实训楼"

    unchanged = await test_client.put(f"/api/classes/{first_id}", json={})
    assert unchanged.status_code == 200
    assert unchanged.json()["name"] == "网络安全 3 班"

    deleted = await test_client.delete(f"/api/classes/{first_id}")
    assert deleted.status_code == 200

    assert (await test_client.get(f"/api/classes/{first_id}")).status_code == 404
    assert (await test_client.put(f"/api/classes/{first_id}", json={})).status_code == 404
    assert (await test_client.delete(f"/api/classes/{first_id}")).status_code == 404


METADATA_CASES = [
    pytest.param(
        "subjects",
        subjects_api,
        "subject",
        "university_course",
        "unsupported",
        "课程设计",
        "软件测试",
        id="subjects",
    ),
    pytest.param(
        "grades",
        grades_api,
        "grade",
        "university",
        "unsupported",
        "2028级",
        "2029级",
        id="grades",
    ),
]


@pytest.mark.api
@pytest.mark.parametrize(
    (
        "resource",
        "api_module",
        "usage_column",
        "valid_category",
        "invalid_category",
        "first_name",
        "second_name",
    ),
    METADATA_CASES,
)
async def test_metadata_crud_protection_and_usage_conflicts(
    test_client,
    test_db,
    monkeypatch,
    resource,
    api_module,
    usage_column,
    valid_category,
    invalid_category,
    first_name,
    second_name,
):
    monkeypatch.setattr(api_module, "db", test_db)
    endpoint = f"/api/{resource}"
    response_key = resource

    invalid = await test_client.post(
        endpoint,
        json={"name": "无效元数据", "category": invalid_category},
    )
    assert invalid.status_code == 400

    first = await test_client.post(
        endpoint,
        json={
            "name": first_name,
            "category": valid_category,
            "description": "初始说明",
        },
    )
    assert first.status_code == 200
    first_body = first.json()
    first_id = first_body["id"]
    assert first_body["sort_order"] == 1
    assert first_body["is_preset"] is False

    duplicate = await test_client.post(
        endpoint,
        json={"name": first_name, "category": valid_category},
    )
    assert duplicate.status_code == 409

    second = await test_client.post(
        endpoint,
        json={"name": second_name, "category": valid_category},
    )
    assert second.status_code == 200
    assert second.json()["sort_order"] == 2

    listed = await test_client.get(endpoint, params={"page": 1, "limit": 1})
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert len(listed.json()[response_key]) == 1

    filtered = await test_client.get(
        endpoint,
        params={"category": valid_category, "page": 1, "limit": 10},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 2

    fetched = await test_client.get(f"{endpoint}/{first_id}")
    assert fetched.status_code == 200
    assert fetched.json()["usage_stats"] == {
        "template_count": 0,
        "lesson_plan_count": 0,
        "textbook_count": 0,
        "batch_task_count": 0,
    }

    renamed = f"{first_name}-更新"
    updated = await test_client.put(
        f"{endpoint}/{first_id}",
        json={"name": renamed, "description": "更新说明"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == renamed
    assert updated.json()["description"] == "更新说明"

    unchanged = await test_client.put(f"{endpoint}/{first_id}", json={})
    assert unchanged.status_code == 200
    assert unchanged.json()["name"] == renamed

    conflict = await test_client.put(
        f"{endpoint}/{first_id}",
        json={"name": second_name},
    )
    assert conflict.status_code == 409

    await test_db.execute(
        f"INSERT INTO lesson_plans (id, title, {usage_column}) VALUES (?, ?, ?)",
        (f"uses-{resource}", "引用元数据的教案", renamed),
        commit=True,
    )
    in_use = await test_client.get(f"{endpoint}/{first_id}")
    assert in_use.status_code == 200
    assert in_use.json()["usage_stats"]["lesson_plan_count"] == 1
    assert (await test_client.delete(f"{endpoint}/{first_id}")).status_code == 409

    await test_db.execute(
        "DELETE FROM lesson_plans WHERE id = ?",
        (f"uses-{resource}",),
        commit=True,
    )
    assert (await test_client.delete(f"{endpoint}/{first_id}")).status_code == 200
    assert (await test_client.get(f"{endpoint}/{first_id}")).status_code == 404
    assert (await test_client.put(f"{endpoint}/{first_id}", json={})).status_code == 404
    assert (await test_client.delete(f"{endpoint}/{first_id}")).status_code == 404

    preset_id = f"preset-{resource}"
    preset_name = f"预设-{resource}"
    timestamp = datetime.datetime.now().isoformat()
    await test_db.execute(
        f"""
        INSERT INTO {resource}
            (id, name, category, is_preset, sort_order, description, created_at, updated_at)
        VALUES (?, ?, ?, 1, 99, NULL, ?, ?)
        """,
        (preset_id, preset_name, valid_category, timestamp, timestamp),
        commit=True,
    )

    description_update = await test_client.put(
        f"{endpoint}/{preset_id}",
        json={"description": "允许修改说明"},
    )
    assert description_update.status_code == 200
    assert description_update.json()["description"] == "允许修改说明"
    assert (
        await test_client.put(
            f"{endpoint}/{preset_id}",
            json={"name": "禁止修改预设名称"},
        )
    ).status_code == 403
    assert (await test_client.delete(f"{endpoint}/{preset_id}")).status_code == 403
