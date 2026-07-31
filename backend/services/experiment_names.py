"""Experiment-name generation and validation for fixed-format plans."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

from ..config import settings
from .ai_provider import generate_with_ai

logger = logging.getLogger(__name__)

EXPERIMENT_NAME_MAX_CHARS = 18
EXPERIMENT_NAME_MAX_DISPLAY_WIDTH = 36
EXPERIMENT_NAME_GENERATION_ATTEMPTS = 3


def _display_width(value: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        for char in value
    )


def _as_dict(chapter: Any) -> dict[str, Any]:
    if hasattr(chapter, "model_dump"):
        return chapter.model_dump()
    return dict(chapter)


def validate_experiment_name(value: str, *, label: str = "实验名称") -> str:
    """Return a clean name or raise when it cannot fit on one template line."""
    raw = str(value or "")
    if "\n" in raw or "\r" in raw:
        raise ValueError(f"{label}不能包含换行")

    name = raw.strip()
    if not name:
        raise ValueError(f"{label}不能为空")
    if "…" in name or re.search(r"\.{3,}", name):
        raise ValueError(f"{label}不能包含省略号")
    if len(name) > EXPERIMENT_NAME_MAX_CHARS:
        raise ValueError(
            f"{label}不能超过 {EXPERIMENT_NAME_MAX_CHARS} 个字符，当前为 {len(name)} 个"
        )
    if _display_width(name) > EXPERIMENT_NAME_MAX_DISPLAY_WIDTH:
        raise ValueError(f"{label}过宽，无法在固定模板中保持单行")
    return name


def validate_experiment_chapters(
    chapters: Iterable[Any],
    *,
    require_every_group: bool,
) -> list[tuple[int, str]]:
    """Validate the merged name for each two-lesson experiment row."""
    values = [_as_dict(chapter) for chapter in chapters]
    projects: list[tuple[int, str]] = []
    for start in range(0, len(values), 2):
        group_number = start // 2 + 1
        names = [
            str(item.get("experiment_name") or "").strip()
            for item in values[start:start + 2]
            if str(item.get("experiment_name") or "").strip()
        ]
        if require_every_group and len(names) != 1:
            raise ValueError(f"第 {group_number} 个实验项目必须且只能有一个实验名称")
        if not names:
            continue
        project = "、".join(names)
        projects.append(
            (
                group_number,
                validate_experiment_name(project, label=f"第 {group_number} 个实验名称"),
            )
        )

    if not projects:
        raise ValueError("实验计划缺少实验名称")
    return projects


def _parse_name_response(content: str) -> list[dict[str, Any]]:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        content = match.group(1)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("实验名称生成结果不是有效 JSON") from exc
    if not isinstance(data, list):
        raise ValueError("实验名称生成结果必须是 JSON 数组")
    return [item for item in data if isinstance(item, dict)]


def _apply_generated_names(
    chapters: list[dict[str, Any]],
    generated: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    group_count = (len(chapters) + 1) // 2
    names_by_group: dict[int, str] = {}
    for item in generated:
        try:
            group_number = int(item.get("group_number") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("实验名称生成结果中的组号无效") from exc
        if group_number in names_by_group:
            raise ValueError(f"第 {group_number} 个实验名称重复")
        names_by_group[group_number] = validate_experiment_name(
            str(item.get("experiment_name") or ""),
            label=f"第 {group_number} 个实验名称",
        )

    expected = set(range(1, group_count + 1))
    if set(names_by_group) != expected:
        raise ValueError("实验名称生成数量与实验项目数量不一致")

    result = [dict(chapter) for chapter in chapters]
    for start in range(0, len(result), 2):
        group_number = start // 2 + 1
        result[start]["experiment_name"] = names_by_group[group_number]
        if start + 1 < len(result):
            result[start + 1]["experiment_name"] = ""
    validate_experiment_chapters(result, require_every_group=True)
    return result


def _build_generation_prompt(chapters: list[dict[str, Any]]) -> str:
    groups = []
    for start in range(0, len(chapters), 2):
        topics = [
            str(item.get("topic") or "").strip()
            for item in chapters[start:start + 2]
            if str(item.get("topic") or "").strip()
        ]
        groups.append(
            {
                "group_number": start // 2 + 1,
                "topics": topics,
            }
        )
    return f"""请为以下每组教学主题重新生成一个简洁、具体、可操作的实验项目名称。

硬性要求：
1. 每个名称最多 {EXPERIMENT_NAME_MAX_CHARS} 个字符，显示宽度最多 {EXPERIMENT_NAME_MAX_DISPLAY_WIDTH}；
2. 不得包含换行、中文省略号或三个连续英文句点；
3. 不要添加“上机实验：”“实验项目：”等前缀；
4. 每组只返回一个名称，不得把多个长标题直接拼接；
5. 只返回 JSON 数组，不要解释。

输入：
{json.dumps(groups, ensure_ascii=False)}

输出格式：
[{{"group_number": 1, "experiment_name": "Python环境配置"}}]
"""


async def ensure_experiment_names(
    chapters: Iterable[Any],
    *,
    provider: str | None,
    api_key: str | None,
    model: str | None,
    require_every_group: bool,
) -> tuple[list[dict[str, Any]], bool]:
    """Validate names and regenerate all group names when validation fails."""
    values = [_as_dict(chapter) for chapter in chapters]
    try:
        validate_experiment_chapters(
            values,
            require_every_group=require_every_group,
        )
        return values, False
    except ValueError as initial_error:
        logger.warning("Experiment names require regeneration: %s", initial_error)

    prompt = _build_generation_prompt(values)
    last_error: Exception | None = None
    for attempt in range(1, EXPERIMENT_NAME_GENERATION_ATTEMPTS + 1):
        try:
            response = await generate_with_ai(
                prompt=prompt,
                system_prompt="你是职业教育课程实验项目命名专家，必须严格遵守字数与格式限制。",
                provider=provider,
                api_key=api_key,
                model=model,
                max_tokens=settings.ai_max_tokens_batch,
            )
            regenerated = _apply_generated_names(values, _parse_name_response(response))
            logger.info("Regenerated %s compliant experiment names", (len(values) + 1) // 2)
            return regenerated, True
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Experiment-name regeneration attempt %s/%s failed: %s",
                attempt,
                EXPERIMENT_NAME_GENERATION_ATTEMPTS,
                exc,
            )

    raise ValueError(
        f"实验名称连续重新生成 {EXPERIMENT_NAME_GENERATION_ATTEMPTS} 次仍不符合单行要求：{last_error}"
    ) from last_error
