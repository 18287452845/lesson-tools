"""
AI generator service for creating textbook chapter outlines.
"""
import json
import re
from typing import Dict, Optional, Any, List

from ..config import settings
from ..models.schemas import (
    TextbookChapterGenerateRequest,
    TextbookChapterCreateRequest,
)
from .ai_provider import AIProviderFactory, generate_with_ai


class TextbookChapterGenerator:
    """
    Generate textbook chapter outlines using AI providers.

    This service handles:
    - AI-powered chapter structure generation
    - ISBN/textbook-based chapter extraction
    - Chapter metadata generation (content summary, key concepts)

    Supports both DeepSeek and Anthropic Claude AI providers.
    """

    # System prompt for textbook chapter generation
    SYSTEM_PROMPT = """你是一位资深的教材研究专家和课程大纲设计专家。
你精通各类教材的章节结构，能够准确生成教材的完整章节大纲。"""

    # Chapter generation prompt template
    CHAPTER_GENERATION_PROMPT = """你是一位资深的教材研究专家和课程大纲设计专家。

请根据以下教材信息，生成该教材的完整章节大纲。

## 教材信息
- 教材名称：{textbook_name}
{isbn_info}
{subject_info}
{grade_info}
{additional_info}

## 任务要求
1. 如果是常见教材（如人教版、苏教版、高等教育出版社教材等），请根据真实章节结构生成
2. 如果是不常见的教材，请根据学科特点和教学规律，合理推断章节结构
3. 结构要完整，除一级大章节外，应尽量识别“节、任务、知识点”等子章节
4. 使用扁平数组表达父子关系，最多支持5级；每项必须提供唯一 client_id，子章节通过 parent_chapter_id 指向父项
5. 每个章节都要提供内容概述和核心概念
6. 合理估算每个章节所需课时数；父子章节课时不要重复累计

## 输出格式要求
请严格按照以下JSON数组格式返回，确保JSON格式正确可解析：

```json
[
  {{
    "client_id": "chapter-1",
    "parent_chapter_id": null,
    "chapter_number": "第1章",
    "chapter_title": "章节标题",
    "content_summary": "内容概述（100-200字，说明本章主要内容和教学目标）",
    "key_concepts": ["核心概念1", "核心概念2", "核心概念3"],
    "hours_required": 8
  }},
  {{
    "client_id": "chapter-1-section-1",
    "parent_chapter_id": "chapter-1",
    "chapter_number": "1.1",
    "chapter_title": "子章节标题",
    "content_summary": "子章节内容概述...",
    "key_concepts": ["概念1", "概念2"],
    "hours_required": 2
  }}
]
```

## 注意事项
1. chapter_number 格式示例："第1章"、"1.1"、"1.1.1"、"第一单元"、"Unit 1"等
2. chapter_title 要准确反映章节核心内容
3. content_summary 要具体，包含教学重点和学习目标
4. key_concepts 至少包含2-5个核心概念
5. hours_required 根据章节内容复杂度合理估算（一般2-8课时）
6. 请确保返回的是纯JSON数组格式，不要包含其他说明文字
7. 一级大章节数量一般在8-16章之间，数量不包含子章节；每个大章节应按真实目录补充下级结构
8. parent_chapter_id 只能引用数组中已经出现的 client_id；一级章节必须为 null

请直接输出JSON数组。
"""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the textbook chapter generator.

        Args:
            provider: AI provider name ('deepseek' or 'anthropic')
            api_key: API key for the provider
            model: Model name to use
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model

    async def generate_chapters(
        self,
        request: TextbookChapterGenerateRequest,
    ) -> List[TextbookChapterCreateRequest]:
        """
        Generate textbook chapters using AI.

        Args:
            request: Textbook chapter generation request with textbook info

        Returns:
            List of generated chapter structures
        """
        prompt = self._build_generation_prompt(request)

        content = await generate_with_ai(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

        chapters_data = self._infer_missing_hierarchy(self._parse_json_response(content))

        # Convert to TextbookChapterCreateRequest objects
        chapters = []
        for idx, chapter_dict in enumerate(chapters_data, 1):
            chapter_dict = dict(chapter_dict)
            # Ensure sort_order is set
            chapter_dict["sort_order"] = idx

            # Ensure key_concepts is a list
            if "key_concepts" not in chapter_dict:
                chapter_dict["key_concepts"] = []
            elif isinstance(chapter_dict["key_concepts"], str):
                # If key_concepts is a string, split by comma
                chapter_dict["key_concepts"] = [
                    k.strip()
                    for k in re.split(r"[,，;；]", chapter_dict["key_concepts"])
                    if k.strip()
                ]

            chapter_dict.setdefault("content_origin", "ai_inferred")
            chapter_dict.setdefault("confidence", 0.7)

            chapters.append(TextbookChapterCreateRequest(**chapter_dict))

        return chapters

    @staticmethod
    def _chapter_number_level(chapter_number: str) -> int:
        normalized = str(chapter_number or "").strip()
        numeric = re.match(r"^(\d+(?:\.\d+){0,4})", normalized)
        if numeric:
            return min(5, numeric.group(1).count(".") + 1)
        if re.match(r"^第.+节", normalized):
            return 2
        if re.match(r"^[一二三四五六七八九十百]+[、.]", normalized):
            return 3
        if re.match(r"^[（(][一二三四五六七八九十百零〇]+[）)]", normalized):
            return 4
        if re.match(r"^(?:[（(]\d+[）)]|\d+[）)])", normalized):
            return 5
        if re.match(r"^任务", normalized):
            return 2
        if re.match(r"^(?:活动|知识点)", normalized):
            return 3
        return 1

    @staticmethod
    def _flatten_chapter_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        flattened: List[Dict[str, Any]] = []
        used_ids: set[str] = set()

        def walk(nodes: List[Dict[str, Any]], parent_id: Optional[str] = None) -> None:
            for raw_item in nodes:
                if not isinstance(raw_item, dict):
                    raise ValueError(f"Invalid chapter item: {raw_item}")
                item = dict(raw_item)
                children = (
                    item.pop("children", None)
                    or item.pop("subchapters", None)
                    or item.pop("sections", None)
                    or []
                )
                base_id = str(item.get("client_id") or f"ai-chapter-{len(flattened) + 1}")
                client_id = base_id
                suffix = 2
                while client_id in used_ids:
                    client_id = f"{base_id}-{suffix}"
                    suffix += 1
                used_ids.add(client_id)
                item["client_id"] = client_id
                if not item.get("parent_chapter_id") and parent_id:
                    item["parent_chapter_id"] = parent_id
                flattened.append(item)
                if isinstance(children, list):
                    walk(children, client_id)

        walk(items)
        return flattened

    def _infer_missing_hierarchy(
        self,
        items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        valid_ids = {str(item.get("client_id")) for item in items if item.get("client_id")}
        last_at_level: Dict[int, str] = {}
        normalized: List[Dict[str, Any]] = []

        for item in items:
            current = dict(item)
            client_id = str(current["client_id"])
            level = self._chapter_number_level(str(current.get("chapter_number") or ""))
            parent_id = current.get("parent_chapter_id")
            if parent_id not in valid_ids or parent_id == client_id:
                parent_id = None
            if not parent_id and level > 1:
                available_levels = [known for known in last_at_level if known < level]
                if available_levels:
                    parent_id = last_at_level[max(available_levels)]
            current["parent_chapter_id"] = parent_id
            normalized.append(current)
            last_at_level[level] = client_id
            for stale_level in range(level + 1, 6):
                last_at_level.pop(stale_level, None)

        return normalized

    def _build_generation_prompt(
        self,
        request: TextbookChapterGenerateRequest,
    ) -> str:
        """Build the chapter generation prompt."""
        # Build optional info sections
        isbn_info = f"- ISBN：{request.isbn}" if request.isbn else ""
        subject_info = f"- 学科：{request.subject}" if request.subject else ""
        grade_info = f"- 年级：{request.grade}" if request.grade else ""
        additional_info = (
            f"- 补充说明：{request.additional_info}"
            if request.additional_info
            else ""
        )

        return self.CHAPTER_GENERATION_PROMPT.format(
            textbook_name=request.textbook_name,
            isbn_info=isbn_info,
            subject_info=subject_info,
            grade_info=grade_info,
            additional_info=additional_info,
        )

    def _parse_json_response(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse JSON array from AI response with robust error handling.

        Handles cases where JSON is wrapped in markdown code blocks
        and tries to fix common JSON formatting issues.
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        else:
            # Try without language specifier
            json_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                # Try to find JSON array directly (look for opening [ and closing ])
                start_idx = content.find('[')
                if start_idx != -1:
                    # Find matching closing bracket
                    bracket_count = 0
                    in_string = False
                    escape_next = False
                    for i in range(start_idx, len(content)):
                        char = content[i]
                        if escape_next:
                            escape_next = False
                            continue
                        if char == '\\':
                            escape_next = True
                            continue
                        if char == '"' and not escape_next:
                            in_string = not in_string
                        elif not in_string:
                            if char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    content = content[start_idx:i+1]
                                    break

        # Parse JSON with multiple fallback attempts
        attempts = [
            # 1. Try parsing as-is
            lambda c: json.loads(c),
            # 2. Try after removing trailing commas
            lambda c: json.loads(re.sub(r",\s*([}\]])", r"\1", c)),
            # 3. Try after fixing unquoted keys
            lambda c: json.loads(re.sub(r"(\w+)\s*:", r'"\1":', c)),
            # 4. Try after removing control characters
            lambda c: json.loads(re.sub(r'[\x00-\x1f\x7f-\x9f]', '', c)),
            # 5. Try after fixing comments
            lambda c: json.loads(re.sub(r'//.*?(\n|$)', '', c)),
            # 6. Try fixing missing commas between array items
            lambda c: json.loads(re.sub(r'([}\]])\s*\n\s*\{', r'\1,\n  {', c)),
            # 7. Try aggressive comma fixing
            lambda c: json.loads(re.sub(r'([}\]])\s+\{', r'\1, {', c)),
        ]

        last_error = None
        for attempt in attempts:
            try:
                result = attempt(content)
                # Validate the result is a list
                if isinstance(result, list):
                    flattened = self._flatten_chapter_items(result)
                    # Validate each item has required fields
                    for item in flattened:
                        if "chapter_number" not in item or "chapter_title" not in item:
                            raise ValueError(
                                f"Chapter missing required fields: {item}"
                            )
                    return flattened
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                continue

        # If all attempts failed, raise the last error
        raise ValueError(
            f"Failed to parse AI response as JSON array. Last error: {last_error}\n"
            f"Content preview (first 500 chars): {content[:500]}..."
        )


async def generate_textbook_chapters(
    request: TextbookChapterGenerateRequest,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> List[TextbookChapterCreateRequest]:
    """
    Convenience function to generate textbook chapters.

    Args:
        request: Textbook chapter generation request
        provider: AI provider name
        api_key: Optional API key
        model: Optional model name

    Returns:
        List of generated chapter structures
    """
    generator = TextbookChapterGenerator(provider, api_key, model)
    return await generator.generate_chapters(request)
