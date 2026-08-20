"""Canonical stored-content helpers shared by lesson and semester artifacts."""

import json
from collections.abc import Mapping
from typing import Any, Dict


def parse_content_layer(raw_content: Any, *, label: str) -> Dict[str, Any]:
    """Parse one optional JSON object layer with a useful source label."""
    if not raw_content:
        return {}
    try:
        content = (
            dict(raw_content)
            if isinstance(raw_content, Mapping)
            else json.loads(raw_content)
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"{label}无法解析") from exc
    if not isinstance(content, dict):
        raise ValueError(f"{label}不是有效对象")
    return content


def merge_lesson_content(
    generated_content: Any,
    final_content: Any,
    *,
    label: str = "教案内容",
) -> Dict[str, Any]:
    """Return generated content with partial final-content fields overlaid."""
    content = parse_content_layer(generated_content, label=f"{label}生成内容")
    content.update(parse_content_layer(final_content, label=f"{label}最终内容"))
    return content
