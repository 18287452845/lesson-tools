"""
AI editor service for modifying existing lesson plan content.
Supports multiple AI providers: DeepSeek and Anthropic Claude.
"""
from typing import Optional, Dict, Any

from .ai_provider import generate_with_ai


class AIEditor:
    """
    Edit and modify lesson plan content using AI providers.

    This service handles:
    - Modifying existing content while preserving meaning
    - Adding missing sections (e.g., teaching reflection)
    - Enhancing content quality
    - Rewriting content based on specific requirements

    Supports both DeepSeek and Anthropic Claude AI providers.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the AI editor.

        Args:
            provider: AI provider name ('deepseek' or 'anthropic')
            api_key: API key for the provider
            model: Model name to use
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model

    async def generate_reflection(
        self,
        context: Dict[str, Any],
    ) -> str:
        """
        Generate a teaching reflection based on lesson plan content.

        Args:
            context: Dictionary with lesson plan context including:
                - subject: Subject
                - topic: Topic
                - grade: Grade level
                - teaching_goals: Teaching goals
                - key_points: Key points
                - difficult_points: Difficult points
                - teaching_process: Teaching process (summary)

        Returns:
            Generated reflection text
        """
        prompt = self._build_reflection_prompt(context)

        return await generate_with_ai(
            prompt=prompt,
            system_prompt="你是一位经验丰富的教学专家，擅长撰写真实、有深度的教学反思。",
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

    async def modify_content(
        self,
        original_content: str,
        modification_request: str,
        context: Dict[str, Any],
        section_name: Optional[str] = None,
    ) -> str:
        """
        Modify content based on user requirements.

        Args:
            original_content: Original content to modify
            modification_request: User's modification request
            context: Context information (subject, topic, grade, etc.)
            section_name: Optional section name for specialized handling

        Returns:
            Modified content
        """
        prompt = self._build_modify_prompt(
            original_content, modification_request, context, section_name
        )

        return await generate_with_ai(
            prompt=prompt,
            system_prompt="你是一位专业的教学设计专家，擅长优化教案内容。",
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

    async def enhance_content(
        self,
        content: str,
        enhancement_type: str,
        context: Dict[str, Any],
        specific_instruction: Optional[str] = None,
    ) -> str:
        """
        Enhance content quality.

        Args:
            content: Content to enhance
            enhancement_type: Type of enhancement ("detailed", "professional", "simplified", "rewrite")
            context: Context information
            specific_instruction: Optional specific instruction

        Returns:
            Enhanced content
        """
        prompt = self._build_enhance_prompt(
            content, enhancement_type, context, specific_instruction
        )

        return await generate_with_ai(
            prompt=prompt,
            system_prompt="你是一位专业的教学设计专家。",
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

    async def generate_missing_section(
        self,
        section_name: str,
        context: Dict[str, Any],
        additional_requirements: Optional[str] = None,
    ) -> str:
        """
        Generate a missing section for an existing lesson plan.

        Args:
            section_name: Name of the section to generate
            context: Context from existing lesson plan
            additional_requirements: Optional additional requirements

        Returns:
            Generated section content
        """
        prompt = self._build_missing_section_prompt(
            section_name, context, additional_requirements
        )

        system_prompt = "你是一位专业的教案设计专家，擅长为教案补充完整的内容。"

        return await generate_with_ai(
            prompt=prompt,
            system_prompt=system_prompt,
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

    async def append_to_section(
        self,
        original_content: str,
        append_content: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Generate content to append to an existing section.

        Args:
            original_content: Original section content
            append_content: Description of what to append
            context: Context information

        Returns:
            Content to append
        """
        prompt = f"""你是{context.get('subject', '')}学科教学专家。

## 原有内容
{original_content}

## 需要添加的内容要求
{append_content}

## 背景
- 学科：{context.get('subject', '')}
- 年级：{context.get('grade', '')}
- 课题：{context.get('topic', '')}

请生成要添加的内容，使其与原有内容自然衔接。
"""

        return await generate_with_ai(
            prompt=prompt,
            system_prompt="你是一位专业的教学设计专家。",
            provider=self.provider,
            api_key=self.api_key,
            model=self.model,
        )

    def _build_reflection_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for generating teaching reflection."""
        # Format teaching goals
        goals = context.get("teaching_goals", {})
        goals_text = ""
        if isinstance(goals, dict):
            if goals.get("knowledge"):
                goals_text += f"知识目标：{'、'.join(goals['knowledge'])}\n"
            if goals.get("ability"):
                goals_text += f"能力目标：{'、'.join(goals['ability'])}\n"
            if goals.get("emotion"):
                goals_text += f"情感目标：{'、'.join(goals['emotion'])}\n"
        elif isinstance(goals, str):
            goals_text = goals

        # Summarize teaching process
        process = context.get("teaching_process", "")
        if len(process) > 500:
            process_summary = process[:500] + "..."
        else:
            process_summary = process

        return f"""你是{context.get('subject', '')}学科教学专家。请根据以下教案信息，撰写一份真实、有深度的教学反思。

## 教案信息
- 课题：{context.get('topic', '')}
- 年级：{context.get('grade', '')}
- 教学目标：
{goals_text}
- 教学重点：{context.get('key_points', '')}
- 教学难点：{context.get('difficult_points', '')}
- 教学过程概要：{process_summary}

## 反思要求
请从以下几个维度进行反思：
1. 目标达成情况
2. 教学方法有效性
3. 学生参与度和反馈
4. 教学亮点与不足
5. 改进措施

请用第一人称撰写，字数300-500字，语言真实自然，避免套话。可以假设一个合理的授课情境。
"""

    def _build_modify_prompt(
        self,
        original_content: str,
        modification_request: str,
        context: Dict[str, Any],
        section_name: Optional[str],
    ) -> str:
        """Build prompt for modifying content."""

        section_headers = {
            "key_points": "教学重点",
            "teaching_process": "教学过程",
        }

        if section_name == "key_points":
            return f"""你是一位课程设计专家。请根据以下要求修改教学重点。

## 原教学重点
{original_content}

## 修改要求
{modification_request}

## 参考信息
- 课题：{context.get('topic', '')}
- 教学目标：{context.get('teaching_goals', '')}

请直接输出修改后的教学重点内容，保持专业性和可操作性。
"""
        elif section_name == "teaching_process":
            return f"""请优化以下教学过程设计，使其更加详细、可操作。

## 原教学过程
{original_content}

## 优化方向
{modification_request}

## 背景信息
- 学科：{context.get('subject', '')}
- 年级：{context.get('grade', '')}
- 课题：{context.get('topic', '')}

请保持原有结构，丰富每个环节的具体操作。
"""

        # General modify prompt
        return f"""请根据用户要求修改以下教案内容。

## 原内容
{original_content}

## 修改要求
{modification_request}

## 上下文信息
- 学科：{context.get('subject', '')}
- 课题：{context.get('topic', '')}

请直接输出修改后的内容，保持专业性。
"""

    def _build_enhance_prompt(
        self,
        content: str,
        enhancement_type: str,
        context: Dict[str, Any],
        specific_instruction: Optional[str],
    ) -> str:
        """Build prompt for enhancing content."""
        enhancement_descriptions = {
            "detailed": "将以下内容写得更详细、具体，增加可操作性和细节描述。",
            "professional": "将以下内容修改得更专业、规范，使用教学专业术语，符合新课标要求。",
            "simplified": "将以下内容简化，提炼核心要点，使其更简洁明了。",
            "rewrite": "重新组织以下内容，使其逻辑更清晰、表达更流畅。",
        }

        description = enhancement_descriptions.get(
            enhancement_type, "优化以下内容。"
        )

        prompt = f"""你是{context.get('subject', '')}学科教学专家。

## 原始内容
{content}

## 优化要求
{description}

"""

        if specific_instruction:
            prompt += f"\n## 特殊要求\n{specific_instruction}\n"

        prompt += f"""
## 背景
- 学科：{context.get('subject', '')}
- 年级：{context.get('grade', '')}
- 课题：{context.get('topic', '')}

请直接输出优化后的内容，不要添加其他说明。
"""

        return prompt

    def _build_missing_section_prompt(
        self,
        section_name: str,
        context: Dict[str, Any],
        additional_requirements: Optional[str],
    ) -> str:
        """Build prompt for generating a missing section."""
        section_headers = {
            "teaching_goals": "教学目标",
            "key_points": "教学重点",
            "difficult_points": "教学难点",
            "teaching_tools": "教具准备",
            "teaching_methods": "教学方法",
            "student_analysis": "学情分析",
            "textbook_analysis": "教材分析",
            "teaching_process": "教学过程",
            "homework": "作业布置",
            "reflection": "教学反思",
            "blackboard_design": "板书设计",
        }

        display_name = section_headers.get(section_name, section_name)

        # Build context summary
        context_summary = f"""
## 教案信息
- 学科：{context.get('subject', '')}
- 年级：{context.get('grade', '')}
- 课题：{context.get('topic', '')}
"""

        # Add relevant context
        if section_name == "reflection":
            if context.get("teaching_goals"):
                goals = context["teaching_goals"]
                if isinstance(goals, dict):
                    goals_text = []
                    if goals.get("knowledge"):
                        goals_text.extend(goals["knowledge"])
                    if goals.get("ability"):
                        goals_text.extend(goals["ability"])
                    if goals.get("emotion"):
                        goals_text.extend(goals["emotion"])
                    context_summary += f"- 教学目标：{'、'.join(goals_text)}\n"
                else:
                    context_summary += f"- 教学目标：{goals}\n"

            if context.get("key_points"):
                context_summary += f"- 教学重点：{context['key_points']}\n"

            if context.get("difficult_points"):
                context_summary += f"- 教学难点：{context['difficult_points']}\n"

            prompt = f"""你是{context.get('subject', '')}学科教学专家。请为这份教案撰写教学反思。

{context_summary}

## 要求
1. 用第一人称撰写
2. 包含：目标达成情况、教学方法效果、学生参与度、亮点与不足、改进措施
3. 字数300-500字
4. 语言真实自然，避免套话
"""

        elif section_name == "blackboard_design":
            prompt = f"""你是{context.get('subject', '')}学科教学专家。请为这份教案设计板书。

{context_summary}

## 要求
1. 突出教学重点和知识结构
2. 简洁明了，逻辑清晰
3. 便于学生记录和记忆
4. 请用文字描述板书的布局和内容
"""

        elif section_name == "teaching_process":
            prompt = f"""你是{context.get('subject', '')}学科教学专家。请为这份教案设计教学过程。

{context_summary}

## 已有信息
"""

            if context.get("teaching_goals"):
                prompt += f"- 教学目标：{context['teaching_goals']}\n"
            if context.get("key_points"):
                prompt += f"- 教学重点：{context['key_points']}\n"
            if context.get("difficult_points"):
                prompt += f"- 教学难点：{context['difficult_points']}\n"

            prompt += """
## 要求
请设计4-5个教学环节，每个环节包含：
- 阶段名称（如：导入新课、探究新知、巩固练习、课堂小结）
- 时间分配
- 教师活动
- 学生活动
- 设计意图

请以JSON数组格式返回：
```json
[
  {
    "stage": "阶段名称",
    "duration": "时间",
    "teacher_activity": "教师活动",
    "student_activity": "学生活动",
    "design_intent": "设计意图"
  }
]
```
"""

        else:
            prompt = f"""你是{context.get('subject', '')}学科教学专家。请为这份教案生成"{display_name}"部分。

{context_summary}

## 要求
1. 内容要具体、可操作
2. 符合{context.get('grade', '')}学生认知水平
3. 与课题"{context.get('topic', '')}"密切相关
"""

        if additional_requirements:
            prompt += f"\n## 特殊要求\n{additional_requirements}\n"

        prompt += "\n请直接输出结果。"

        return prompt


# Convenience functions
async def generate_reflection(
    context: Dict[str, Any],
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Generate a teaching reflection."""
    editor = AIEditor(provider, api_key)
    return await editor.generate_reflection(context)


async def modify_content(
    original_content: str,
    modification_request: str,
    context: Dict[str, Any],
    section_name: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Modify content based on requirements."""
    editor = AIEditor(provider, api_key)
    return await editor.modify_content(
        original_content, modification_request, context, section_name
    )
