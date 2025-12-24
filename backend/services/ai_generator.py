"""
AI generator service for creating lesson plans using multiple AI providers (DeepSeek, Anthropic).
"""
import json
import re
from typing import Dict, Optional, Any

from ..config import settings
from ..models.schemas import (
    LessonPlanInput,
    GeneratedContent,
)
from .ai_provider import AIProviderFactory, generate_with_ai


class AIGenerator:
    """
    Generate lesson plan content using AI providers.

    This service handles:
    - Full lesson plan generation
    - Single field regeneration
    - Content optimization

    Supports both DeepSeek and Anthropic Claude AI providers.
    """

    # System prompt for lesson plan generation
    SYSTEM_PROMPT = """你是一位专业的教案设计专家，擅长根据课程标准和学生实际情况设计高质量的教案。
你需要生成结构完整、内容详实、可操作性强的教案。"""

    # Generation prompt template
    GENERATION_PROMPT = """你是一位资深的{subject}学科教研专家，拥有20年教学经验。
请根据以下信息，生成一份专业、详细、可操作性强的教案。

## 基本信息
- 学科：{subject}
- 年级：{grade}
- 课题：{topic}
- 课时：{duration}
{extra_info}

## 学情参考
{prior_knowledge}

## 教师要求
{additional_requirements}

## 输出要求
请严格按照以下JSON格式返回，确保JSON格式正确可解析：

```json
{{
  "teaching_goals": {{
    "knowledge": ["知识目标1", "知识目标2"],
    "ability": ["能力目标1", "能力目标2"],
    "emotion": ["情感态度价值观目标1"]
  }},
  "key_points": "教学重点内容，要具体明确",
  "difficult_points": "教学难点内容，说明难在哪里",
  "teaching_tools": "教具和学具准备清单",
  "teaching_methods": "采用的教学方法",
  "student_analysis": "学情分析，包括认知基础、可能的困难",
  "textbook_analysis": "教材分析，说明本课在单元/教材中的地位",
  "teaching_steps": [
    {{
      "stage": "导入新课",
      "duration": "5分钟",
      "teacher_activity": "教师具体做什么、说什么",
      "student_activity": "学生具体做什么",
      "design_intent": "这样设计的教育目的"
    }},
    {{
      "stage": "探究新知",
      "duration": "20分钟",
      "teacher_activity": "...",
      "student_activity": "...",
      "design_intent": "..."
    }},
    {{
      "stage": "巩固练习",
      "duration": "12分钟",
      "teacher_activity": "...",
      "student_activity": "...",
      "design_intent": "..."
    }},
    {{
      "stage": "课堂小结",
      "duration": "3分钟",
      "teacher_activity": "...",
      "student_activity": "...",
      "design_intent": "..."
    }}
  ],
  "homework": {{
    "required": "必做作业",
    "optional": "选做作业/拓展"
  }},
  "blackboard_design": "板书设计的文字描述或结构",
  "reflection": "（待课后填写）"
}}
```

注意事项：
1. 教学目标要具体、可测量、可评价
2. 教学过程要详细到可以直接使用
3. 时间分配要合理，总时长匹配课时
4. 语言要专业但不晦涩
5. 要体现新课标理念和学生主体地位
6. 请确保返回的是纯JSON格式，不要包含其他说明文字
"""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the AI generator.

        Args:
            provider: AI provider name ('deepseek' or 'anthropic')
            api_key: API key for the provider
            model: Model name to use
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model

    async def generate_lesson_plan(
        self,
        input_data: LessonPlanInput,
    ) -> GeneratedContent:
        """
        Generate a complete lesson plan.

        Args:
            input_data: Lesson plan input information

        Returns:
            Generated lesson plan content
        """
        prompt = self._build_generation_prompt(input_data)

        content = await generate_with_ai(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

        parsed_data = self._parse_json_response(content)
        return GeneratedContent(**parsed_data)

    async def regenerate_field(
        self,
        input_data: LessonPlanInput,
        field_name: str,
        current_content: Dict[str, Any],
        additional_instruction: Optional[str] = None,
    ) -> str:
        """
        Regenerate a single field.

        Args:
            input_data: Original lesson plan input
            field_name: Name of the field to regenerate
            current_content: Current generated content (for context)
            additional_instruction: Additional instructions for regeneration

        Returns:
            New content for the field
        """
        prompt = self._build_field_prompt(
            input_data, field_name, current_content, additional_instruction
        )

        return await generate_with_ai(
            prompt=prompt,
            system_prompt="你是一位专业的教案设计专家。",
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

    async def optimize_field(
        self,
        input_data: LessonPlanInput,
        field_name: str,
        content: str,
        optimization_type: str = "detailed",
    ) -> str:
        """
        Optimize a field's content.

        Args:
            input_data: Lesson plan input
            field_name: Name of the field
            content: Current content
            optimization_type: Type of optimization ("detailed", "concise", "professional")

        Returns:
            Optimized content
        """
        prompt = self._build_optimization_prompt(
            input_data, field_name, content, optimization_type
        )

        return await generate_with_ai(
            prompt=prompt,
            system_prompt="你是一位专业的教学设计专家。",
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

    def _build_generation_prompt(self, input_data: LessonPlanInput) -> str:
        """Build the full lesson plan generation prompt."""
        extra_info = ""
        if input_data.textbook_version:
            extra_info += f"- 教材版本：{input_data.textbook_version}\n"
        if input_data.unit_name:
            extra_info += f"- 单元：{input_data.unit_name}\n"

        prior_knowledge = input_data.prior_knowledge or "无特殊说明"
        additional_requirements = input_data.additional_requirements or "无特殊要求"

        return self.GENERATION_PROMPT.format(
            subject=input_data.subject,
            grade=input_data.grade,
            topic=input_data.topic,
            duration=input_data.duration,
            extra_info=extra_info,
            prior_knowledge=prior_knowledge,
            additional_requirements=additional_requirements,
        )

    def _build_field_prompt(
        self,
        input_data: LessonPlanInput,
        field_name: str,
        current_content: Dict[str, Any],
        additional_instruction: Optional[str],
    ) -> str:
        """Build a prompt for regenerating a single field."""
        field_display_names = {
            "teaching_goals": "教学目标",
            "key_points": "教学重点",
            "difficult_points": "教学难点",
            "teaching_tools": "教具准备",
            "teaching_methods": "教学方法",
            "student_analysis": "学情分析",
            "textbook_analysis": "教材分析",
            "teaching_steps": "教学过程",
            "homework": "作业布置",
            "blackboard_design": "板书设计",
            "reflection": "教学反思",
        }

        display_name = field_display_names.get(field_name, field_name)

        prompt = f"""你是一位资深的{input_data.subject}学科教研专家。

## 当前教案信息
- 学科：{input_data.subject}
- 年级：{input_data.grade}
- 课题：{input_data.topic}
- 课时：{input_data.duration}

## 任务
请重新生成教案的"{display_name}"部分。

"""

        if additional_instruction:
            prompt += f"\n## 特殊要求\n{additional_instruction}\n"

        # Add context from other fields
        if field_name != "teaching_goals" and "teaching_goals" in current_content:
            goals = current_content["teaching_goals"]
            if isinstance(goals, dict):
                prompt += f"\n## 参考信息\n教学目标：\n"
                if goals.get("knowledge"):
                    prompt += f"- 知识与技能：{'、'.join(goals['knowledge'])}\n"
                if goals.get("ability"):
                    prompt += f"- 过程与方法：{'、'.join(goals['ability'])}\n"
                if goals.get("emotion"):
                    prompt += f"- 情感态度价值观：{'、'.join(goals['emotion'])}\n"

        # Add specific instructions based on field
        if field_name == "teaching_steps":
            prompt += """
## 教学过程要求
请返回JSON格式的教学步骤数组：
```json
[
  {
    "stage": "阶段名称",
    "duration": "时间分配",
    "teacher_activity": "教师活动",
    "student_activity": "学生活动",
    "design_intent": "设计意图"
  }
]
```
"""
        elif field_name == "teaching_goals":
            prompt += """
## 教学目标要求
请返回JSON格式的教学目标：
```json
{
  "knowledge": ["知识目标1", "知识目标2"],
  "ability": ["能力目标1", "能力目标2"],
  "emotion": ["情感态度价值观目标1"]
}
```
"""
        elif field_name == "homework":
            prompt += """
## 作业要求
请返回JSON格式的作业：
```json
{
  "required": "必做作业",
  "optional": "选做作业（可选）"
}
```
"""

        prompt += "\n请直接输出结果，确保格式正确。"

        return prompt

    def _build_optimization_prompt(
        self,
        input_data: LessonPlanInput,
        field_name: str,
        content: str,
        optimization_type: str,
    ) -> str:
        """Build a prompt for optimizing content."""
        optimization_prompts = {
            "detailed": "请将以下内容写得更详细、更具体，增加可操作性。",
            "concise": "请将以下内容精简，保留核心要点，使其更简洁。",
            "professional": "请将以下内容修改得更专业、更规范，使用教学专业术语。",
            "engaging": "请将以下内容修改得更有趣、更能吸引学生注意力。",
        }

        instruction = optimization_prompts.get(
            optimization_type, "请优化以下内容。"
        )

        return f"""你是一位教学设计专家。

## 原始内容
{content}

## 优化要求
{instruction}

## 背景
- 学科：{input_data.subject}
- 年级：{input_data.grade}
- 课题：{input_data.topic}

请直接输出优化后的内容，不要添加其他说明。
"""

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """
        Parse JSON from AI response.

        Handles cases where JSON is wrapped in markdown code blocks.
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

        # Parse JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Try to fix common JSON errors
            # Remove trailing commas
            content = re.sub(r",\s*([}\]])", r"\1", content)
            # Fix unquoted keys
            content = re.sub(r"(\w+)\s*:", r'"\1":', content)

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                raise ValueError(f"Failed to parse AI response as JSON: {e}")


async def generate_lesson_plan(
    input_data: LessonPlanInput,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> GeneratedContent:
    """
    Convenience function to generate a lesson plan.

    Args:
        input_data: Lesson plan input
        provider: AI provider name
        api_key: Optional API key
        model: Optional model name

    Returns:
        Generated content
    """
    generator = AIGenerator(provider, api_key, model)
    return await generator.generate_lesson_plan(input_data)
