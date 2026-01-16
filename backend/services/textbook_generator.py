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
3. 结构要完整，覆盖该教材所有主要章节
4. 每个章节都要提供内容概述和核心概念
5. 合理估算每个章节所需课时数

## 输出格式要求
请严格按照以下JSON数组格式返回，确保JSON格式正确可解析：

```json
[
  {{
    "chapter_number": "第1章",
    "chapter_title": "章节标题",
    "content_summary": "内容概述（100-200字，说明本章主要内容和教学目标）",
    "key_concepts": ["核心概念1", "核心概念2", "核心概念3"],
    "hours_required": 4
  }},
  {{
    "chapter_number": "第2章",
    "chapter_title": "章节标题",
    "content_summary": "内容概述...",
    "key_concepts": ["概念1", "概念2"],
    "hours_required": 6
  }}
]
```

## 注意事项
1. chapter_number 格式示例："第1章"、"第2章"、"第一单元"、"Unit 1"等
2. chapter_title 要准确反映章节核心内容
3. content_summary 要具体，包含教学重点和学习目标
4. key_concepts 至少包含2-5个核心概念
5. hours_required 根据章节内容复杂度合理估算（一般2-8课时）
6. 请确保返回的是纯JSON数组格式，不要包含其他说明文字
7. 章节数量一般在8-16章之间，根据教材实际情况决定

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

        chapters_data = self._parse_json_response(content)

        # Convert to TextbookChapterCreateRequest objects
        chapters = []
        for idx, chapter_dict in enumerate(chapters_data, 1):
            # Ensure sort_order is set
            if "sort_order" not in chapter_dict:
                chapter_dict["sort_order"] = idx

            # Ensure key_concepts is a list
            if "key_concepts" not in chapter_dict:
                chapter_dict["key_concepts"] = []
            elif isinstance(chapter_dict["key_concepts"], str):
                # If key_concepts is a string, split by comma
                chapter_dict["key_concepts"] = [
                    k.strip() for k in chapter_dict["key_concepts"].split(",")
                ]

            chapters.append(TextbookChapterCreateRequest(**chapter_dict))

        return chapters

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
                    # Validate each item has required fields
                    for item in result:
                        if not isinstance(item, dict):
                            raise ValueError(f"Invalid chapter item: {item}")
                        if "chapter_number" not in item or "chapter_title" not in item:
                            raise ValueError(
                                f"Chapter missing required fields: {item}"
                            )
                    return result
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
