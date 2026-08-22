"""AI condensation of lesson focus/difficulty text for fixed-template plans.

The teaching-plan template keeps one point per line with at most 25 characters.
Long single clauses are re-summarised by AI instead of being hard-truncated,
and missing focus/difficulty text is generated from the lesson topic.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterable

from ..config import settings
from .ai_provider import generate_with_ai

logger = logging.getLogger(__name__)

POINT_BRIEF_MAX_CHARS = 25
POINT_BRIEF_MAX_LINES = 2
POINT_BRIEF_GENERATION_ATTEMPTS = 3


def point_lines_ok(value: Any) -> bool:
    """True when the text exists and every line fits the template limit."""
    text = str(value or "").strip()
    if not text:
        return False
    return all(
        len(line.strip()) <= POINT_BRIEF_MAX_CHARS
        for line in text.splitlines()
        if line.strip()
    )


def chapter_points_ok(chapter: Any) -> bool:
    item = chapter if isinstance(chapter, dict) else dict(chapter)
    return point_lines_ok(item.get("key_points")) and point_lines_ok(
        item.get("difficult_points")
    )


def _clean_lines(value: Any, *, label: str) -> str:
    lines = [
        line.strip()
        for line in str(value or "").replace("；", "\n").splitlines()
        if line.strip()
    ]
    if not lines:
        raise ValueError(f"{label}不能为空")
    for line in lines:
        if len(line) > POINT_BRIEF_MAX_CHARS:
            raise ValueError(
                f"{label}单行不能超过 {POINT_BRIEF_MAX_CHARS} 个字符"
            )
    return "\n".join(lines[:POINT_BRIEF_MAX_LINES])


def _parse_response(content: str) -> list[dict[str, Any]]:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        content = match.group(1)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("重难点精简结果不是有效 JSON") from exc
    if not isinstance(data, list):
        raise ValueError("重难点精简结果必须是 JSON 数组")
    return [item for item in data if isinstance(item, dict)]


def _apply_briefs(
    chapters: list[dict[str, Any]],
    targets: list[int],
    generated: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Overwrite key/difficult points only for the targeted lesson indexes."""
    briefs_by_number: dict[int, tuple[str, str]] = {}
    for item in generated:
        try:
            number = int(item.get("lesson_number") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("重难点精简结果中的课序无效") from exc
        if number in briefs_by_number:
            raise ValueError(f"第 {number} 份教案的重难点结果重复")
        briefs_by_number[number] = (
            _clean_lines(
                item.get("key_points"), label=f"第 {number} 份教案重点"
            ),
            _clean_lines(
                item.get("difficult_points"), label=f"第 {number} 份教案难点"
            ),
        )

    expected = {int(chapters[index].get("lesson_number") or 0) for index in targets}
    if set(briefs_by_number) != expected:
        raise ValueError("重难点精简结果数量与待精简教案数量不一致")

    result: list[dict[str, Any]] = []
    for chapter in chapters:
        number = int(chapter.get("lesson_number") or 0)
        merged = dict(chapter)
        if number in briefs_by_number:
            key_points, difficult_points = briefs_by_number[number]
            merged["key_points"] = key_points
            merged["difficult_points"] = difficult_points
        result.append(merged)
    return result


def _build_prompt(chapters: list[dict[str, Any]]) -> str:
    payload = [
        {
            "lesson_number": chapter.get("lesson_number"),
            "topic": chapter.get("topic") or "",
            "key_points": chapter.get("key_points") or "",
            "difficult_points": chapter.get("difficult_points") or "",
        }
        for chapter in chapters
    ]
    return f"""请把以下每份教案的“教学重点”和“教学难点”改写为固定模板可用的简短版本。

硬性要求：
1. 重点、难点各输出 1-2 行，每行一个完整要点；
2. 每行不超过 {POINT_BRIEF_MAX_CHARS} 个字符（含标点）；
3. 忠于原意，保留最核心的要点，不得编造原文没有的内容；
4. 原文为空或过长时，依据课题概括生成一条最核心的要点；
5. 重点和难点都不能为空；
6. 只返回 JSON 数组，不要解释。

输入：
{json.dumps(payload, ensure_ascii=False)}

输出格式：
[{{"lesson_number": 1, "key_points": "掌握VLAN的基本概念", "difficult_points": "理解Trunk链路的转发过程"}}]
"""


async def ensure_brief_points(
    chapters: Iterable[Any],
    *,
    provider: str | None,
    api_key: str | None,
    model: str | None,
) -> tuple[list[dict[str, Any]], bool]:
    """Condense focus/difficulty lines via AI when any lesson exceeds the limit.

    Only non-compliant lessons are sent to the AI so large batches stay fast.
    """
    values = [
        chapter if isinstance(chapter, dict) else dict(chapter)
        for chapter in chapters
    ]
    targets = [
        index for index, chapter in enumerate(values) if not chapter_points_ok(chapter)
    ]
    if not targets:
        return values, False

    prompt = _build_prompt([values[index] for index in targets])
    last_error: Exception | None = None
    for attempt in range(1, POINT_BRIEF_GENERATION_ATTEMPTS + 1):
        try:
            response = await generate_with_ai(
                prompt=prompt,
                system_prompt="你是职业教育课程重难点提炼专家，必须严格遵守每行字数与格式限制。",
                provider=provider,
                api_key=api_key,
                model=model,
                max_tokens=settings.ai_max_tokens_batch,
            )
            condensed = _apply_briefs(values, targets, _parse_response(response))
            logger.info(
                "Condensed focus/difficulty lines for %s of %s lessons",
                len(targets),
                len(values),
            )
            return condensed, True
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Focus/difficulty condensation attempt %s/%s failed: %s",
                attempt,
                POINT_BRIEF_GENERATION_ATTEMPTS,
                exc,
            )

    raise ValueError(
        f"重难点精简连续 {POINT_BRIEF_GENERATION_ATTEMPTS} 次仍不符合每行 "
        f"{POINT_BRIEF_MAX_CHARS} 字要求：{last_error}"
    ) from last_error
