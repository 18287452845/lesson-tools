"""Normalize professional-class selections used by batch generation."""

from __future__ import annotations

import re
from collections import OrderedDict
from collections.abc import Iterable, Sequence


def clean_text_values(values: Iterable[str]) -> list[str]:
    """Trim, remove empty values, and preserve the first occurrence order."""
    cleaned: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def build_class_names(
    grade: str,
    majors: Sequence[str],
    class_numbers: Sequence[int],
) -> list[str]:
    """Build concrete class names for every selected major/class-number pair."""
    clean_majors = clean_text_values(majors)
    clean_numbers = list(dict.fromkeys(int(number) for number in class_numbers))
    return [
        f"{grade.strip()}{major}{number}班"
        for major in clean_majors
        for number in clean_numbers
    ]


def join_display_values(values: Iterable[str]) -> str:
    """Join user-facing multi-value text with a Chinese comma."""
    return "，".join(clean_text_values(values))


def format_class_names(class_names: Sequence[str]) -> str:
    """Compact numbered classes per major and comma-separate different majors.

    Examples:
    ``2024级信息安全技术应用1班`` and ``...2班`` become
    ``2024级信息安全技术应用1、2班``. Classes from another major form a
    separate comma-delimited group.
    """
    groups: OrderedDict[str, list[str]] = OrderedDict()
    standalone: list[str] = []
    pattern = re.compile(r"^(.*?)([1-5])班$")

    for name in clean_text_values(class_names):
        match = pattern.fullmatch(name)
        if not match:
            standalone.append(name)
            continue
        prefix, number = match.groups()
        groups.setdefault(prefix, [])
        if number not in groups[prefix]:
            groups[prefix].append(number)

    compact = [f"{prefix}{'、'.join(numbers)}班" for prefix, numbers in groups.items()]
    compact.extend(standalone)
    return "，".join(compact)
