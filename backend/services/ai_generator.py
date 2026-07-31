"""
AI generator service for creating lesson plans using multiple AI providers (DeepSeek, Anthropic).
"""
import asyncio
import json
import logging
import re
from typing import Dict, Optional, Any, List

from ..config import settings
from ..models.schemas import (
    LessonPlanInput,
    GeneratedContent,
    FieldConfig,
)
from .ai_provider import AIProviderFactory, generate_with_ai

logger = logging.getLogger(__name__)


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

    _STAGE_ALIASES = {
        "导入新课": "新课预热",
        "探究新知": "传授新知",
        "巩固练习": "课堂实践",
        "课堂小结": "课堂总结",
    }
    _STAGE_DURATIONS = {
        "新课预热": "5分钟",
        "问题导入": "5分钟",
        "传授新知": "30分钟",
        "课堂实践": "30分钟",
        "课堂总结": "5分钟",
    }
    _CORE_STAGE_MIN_CHARS = {
        "传授新知": {"teacher_activity": 120, "student_activity": 80},
        "课堂实践": {"teacher_activity": 80, "student_activity": 120},
    }

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
    "knowledge": ["具体的知识目标1（至少2-3条）", "知识目标2"],
    "ability": ["具体的能力目标1（至少2-3条）", "能力目标2"],
    "quality": ["具体的素质目标1（至少2条）", "素质目标2"]
  }},
  "key_points": "教学重点内容，要具体明确",
  "difficult_points": "教学难点内容，说明难在哪里",
  "ideological_political": "结合本节课内容，挖掘课程思政元素，如：工匠精神、生态意识、家国情怀等",
  "teaching_tools": "教具和学具准备清单",
  "teaching_methods": "采用的教学方法",
  "student_analysis": "学情分析，包括认知基础、可能的困难",
  "textbook_analysis": "教材分析，说明本课在单元/教材中的地位",
  "teaching_steps": [
    {{
      "stage": "新课预热",
      "duration": "5分钟",
      "teacher_activity": "【教师】教师具体做什么、说什么",
      "student_activity": "【学生】学生具体做什么",
      "design_intent": "这样设计的教育目的"
    }},
    {{
      "stage": "问题导入",
      "duration": "5分钟",
      "teacher_activity": "【教师】...",
      "student_activity": "【学生】...",
      "design_intent": "..."
    }},
    {{
      "stage": "传授新知",
      "duration": "30分钟",
      "teacher_activity": "【教师】围绕核心原理、配置步骤、示范案例、易错点和验证方法展开完整讲解，不少于120个汉字",
      "student_activity": "【学生】按照任务单观察、记录、回答、同步操作并核对结果，不少于80个汉字",
      "design_intent": "说明知识建构、操作示范与证据验证之间的教学逻辑"
    }},
    {{
      "stage": "课堂实践",
      "duration": "30分钟",
      "teacher_activity": "【教师】发布分层实践任务，明确步骤、验收标准、故障排查方法并巡回指导，不少于80个汉字",
      "student_activity": "【学生】独立或小组完成配置、排错、结果验证、证据留存和互评改进，不少于120个汉字",
      "design_intent": "说明实践任务如何形成岗位能力、规范意识与质量意识"
    }},
    {{
      "stage": "课堂总结",
      "duration": "5分钟",
      "teacher_activity": "【教师】...",
      "student_activity": "【学生】...",
      "design_intent": "..."
    }}
  ],
  "homework": {{
    "required": "必做作业",
    "optional": "选做作业/拓展"
  }},
  "blackboard_design": "板书设计的文字描述或结构",
  "reflection": "（待课后填写）",
  "online_resources": "与本课相关的网络资源链接，如在线课程、教学视频、参考资料网站等（提供2-4个有效的URL链接或资源名称）"
}}
```

注意事项：
1. 教学目标要具体、可测量、可评价
2. 教学过程要详细到可以直接使用；传授新知和课堂实践必须写满教学动作、任务步骤、检查标准与学习产出
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
        field_configs: Optional[List[FieldConfig]] = None,
        generate_reflection: bool = False,
    ) -> GeneratedContent:
        """
        Generate a complete lesson plan.

        Args:
            input_data: Lesson plan input information
            field_configs: Optional list of field configurations from template
                         If provided, will generate dynamic fields based on template

        Returns:
            Generated lesson plan content
        """
        base_prompt = self._build_generation_prompt(input_data, field_configs, generate_reflection)
        retry_prompt_suffix = (
            "\n\n## 输出要求补充\n"
            "- 仅返回严格的JSON对象，不要使用Markdown代码块或任何说明文字\n"
            "- 所有字符串必须正确转义，避免出现控制字符或不合法的转义序列\n"
            "- 不要添加多余的字段或注释\n"
        )

        max_attempts = settings.ai_max_retries + 1
        last_error: Optional[Exception] = None

        for attempt in range(max_attempts):
            prompt = base_prompt
            if attempt:
                prompt = f"{base_prompt}{retry_prompt_suffix}"
                if last_error:
                    prompt += f"- 上一次输出未达到内容质量要求：{last_error}\n请逐项补足后重新生成。\n"
            content = await generate_with_ai(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                provider=self.provider,
                api_key=self.api_key,
                model=self.model,
                response_format={"type": "json_object"},
            )

            try:
                parsed_data = self._parse_json_response(content)
                self._normalize_teaching_steps(parsed_data)
                self._validate_teaching_step_detail(parsed_data)
                return GeneratedContent(**parsed_data)
            except ValueError as e:
                last_error = e
                cleaned_content = self._clean_ai_response(content)
                if cleaned_content != content:
                    try:
                        parsed_data = self._parse_json_response(cleaned_content)
                        self._normalize_teaching_steps(parsed_data)
                        self._validate_teaching_step_detail(parsed_data)
                        return GeneratedContent(**parsed_data)
                    except ValueError as cleaned_error:
                        last_error = cleaned_error

                if attempt >= max_attempts - 1:
                    break

                delay = settings.ai_retry_delay * (settings.ai_retry_backoff ** attempt)
                logger.warning(
                    "AI response parse failed on attempt %s/%s: %s. Retrying in %.1fs.",
                    attempt + 1,
                    max_attempts,
                    last_error,
                    delay,
                )
                await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise ValueError("Failed to parse AI response as JSON after retries.")

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

    def _build_generation_prompt(
        self,
        input_data: LessonPlanInput,
        field_configs: Optional[List[FieldConfig]] = None,
        generate_reflection: bool = False,
    ) -> str:
        """Build the full lesson plan generation prompt with dynamic fields support."""
        extra_info = ""
        if input_data.textbook_name:
            extra_info += f"- 教材：{input_data.textbook_name}\n"
        if input_data.unit_name:
            extra_info += f"- 单元：{input_data.unit_name}\n"
        if input_data.location:
            extra_info += f"- 授课地点：{input_data.location}\n"

        prior_knowledge = input_data.prior_knowledge or "无特殊说明"
        additional_requirements = input_data.additional_requirements or "无特殊要求"

        # Build JSON template based on field configs
        if field_configs:
            json_template = self._build_dynamic_json_template(field_configs, generate_reflection)
            notes = self._build_field_generation_notes(field_configs, generate_reflection)
            required_fields_note = self._build_required_fields_note(field_configs)
        else:
            # Fallback to default template
            json_template = self._get_default_json_template(generate_reflection)
            notes = self._get_default_generation_notes(generate_reflection)
            required_fields_note = ""

        return f"""你是一位资深的{input_data.subject}学科教研专家，拥有20年教学经验。
请根据以下信息，生成一份专业、详细、可操作性强的教案。

## 基本信息
- 学科：{input_data.subject}
- 年级：{input_data.grade}
- 课题：{input_data.topic}
- 课时：{input_data.duration}
{extra_info}

## 学情参考
{prior_knowledge}

## 教师要求
{additional_requirements}

## 输出要求
请严格按照以下JSON格式返回，确保JSON格式正确可解析：

```json
{json_template}
```

{notes}

{required_fields_note}

## 重要注意事项
1. **必须生成JSON中的所有字段**，不允许遗漏任何字段
2. 教学目标要具体、可测量、可评价
   - teaching_goals必须包含knowledge（知识目标）、ability（能力目标）、quality（素质目标）三个字段
   - 每个字段至少包含2-3条具体目标，使用数组格式
3. **教学过程必须包含5个完整阶段，每个阶段的stage值必须严格使用以下标准名称**：
   - 第1阶段："新课预热"（课前准备、复习铺垫，5分钟）
   - 第2阶段："问题导入"（提出问题、创设情境，5-8分钟）
   - 第3阶段："传授新知"（讲授核心内容，固定30分钟）
   - 第4阶段："课堂实践"（实践操作、练习巩固，固定30分钟）
   - 第5阶段："课堂总结"（总结回顾、布置作业，5分钟）
   - **关键要求**：
     * 必须包含所有5个阶段，缺一不可
     * stage字段的值必须是上述标准名称之一，不要添加编号、说明或其他文字
     * 每个阶段都要有详细的teacher_activity、student_activity和design_intent
     * teacher_activity必须以“【教师】”开头，student_activity必须以“【学生】”开头
     * “传授新知”教师活动不少于120个汉字、学生活动不少于80个汉字，至少覆盖核心原理、操作演示、易错点和结果验证
     * “课堂实践”教师活动不少于80个汉字、学生活动不少于120个汉字，至少覆盖任务要求、操作步骤、故障排查、验收标准和证据留存
     * 活动内容使用完整语句和分号组织，不要插入空白行
4. 教学过程要详细到可以直接使用，每个步骤包含教师活动、学生活动和设计意图
5. 时间分配要合理，总时长匹配课时（{input_data.duration}）
6. 语言要专业但不晦涩
7. 要体现新课标理念和学生主体地位
8. 请确保返回的是纯JSON格式，不要包含其他说明文字
9. 对于每个字段都要提供有价值的具体内容，不要使用"待补充"、"根据实际情况"等占位符
10. 所有字段的内容要相互关联、逻辑一致
"""

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
            "ideological_political": "课程思政",
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
                # Support both quality and emotion for backward compatibility
                if goals.get("quality"):
                    prompt += f"- 素质目标：{'、'.join(goals['quality'])}\n"
                elif goals.get("emotion"):
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
请返回JSON格式的教学目标，包含knowledge（知识目标）、ability（能力目标）、quality（素质目标）三个子字段：
```json
{
  "knowledge": ["具体的知识目标1（至少2-3条）", "知识目标2"],
  "ability": ["具体的能力目标1（至少2-3条）", "能力目标2"],
  "quality": ["具体的素质目标1（至少2条）", "素质目标2"]
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

    def _build_dynamic_json_template(self, field_configs: List[FieldConfig], generate_reflection: bool = False) -> str:
        """Build JSON template based on field configurations."""
        template_parts = []

        for field in field_configs:
            field_name = field.name
            field_type = field.field_type

            # Generate sample value based on field type and name
            if field_name == "teaching_goals":
                sample = """{
    "knowledge": ["具体的知识目标1（至少2-3条）", "知识目标2"],
    "ability": ["具体的能力目标1（至少2-3条）", "能力目标2"],
    "quality": ["具体的素质目标1（至少2条）", "素质目标2"]
  }"""
            elif field_name == "reflection":
                # Use different reflection description based on generate_reflection
                if generate_reflection:
                    sample = '"对本节课教学效果的反思，包括成功之处、不足及改进措施（至少2-3条）"'
                else:
                    sample = '"（待课后填写）"'
            elif field_name == "teaching_steps":
                sample = """[
    {
      "stage": "新课预热",
      "duration": "3-5分钟",
      "teacher_activity": "【教师】课前准备、复习旧知、激发兴趣的具体活动（详细描述）",
      "student_activity": "【学生】回顾、准备、参与互动的具体活动（详细描述）",
      "design_intent": "激发学习兴趣，做好知识衔接"
    },
    {
      "stage": "问题导入",
      "duration": "5-8分钟",
      "teacher_activity": "【教师】提出核心问题、创设情境、引导思考的具体内容（详细描述）",
      "student_activity": "【学生】观察、思考、讨论问题的具体活动（详细描述）",
      "design_intent": "引出本课主题，激发探究欲望"
    },
    {
      "stage": "传授新知",
      "duration": "30分钟",
      "teacher_activity": "【教师】围绕核心原理、操作步骤、示范案例、易错点和验证方法进行完整讲解，不少于120个汉字",
      "student_activity": "【学生】依据任务单观察、记录、回答、同步操作并核对验证结果，不少于80个汉字",
      "design_intent": "帮助学生建立原理、操作与验证证据之间的联系"
    },
    {
      "stage": "课堂实践",
      "duration": "30分钟",
      "teacher_activity": "【教师】发布分层任务，明确步骤、验收标准和故障排查方法并巡回指导，不少于80个汉字",
      "student_activity": "【学生】完成配置、排错、结果验证、证据留存、互评和改进，不少于120个汉字",
      "design_intent": "巩固所学知识，培养岗位实践、协作和质量验收能力"
    },
    {
      "stage": "课堂总结",
      "duration": "5分钟",
      "teacher_activity": "【教师】系统总结要点、强调重难点、布置作业的详细内容...",
      "student_activity": "【学生】回顾总结、自我评价、提出疑问的详细内容...",
      "design_intent": "帮助学生梳理知识体系，形成完整认知..."
    }
  ]"""
            elif field_name == "homework":
                sample = """{
    "required": "必做作业",
    "optional": "选做作业/拓展"
  }"""
            elif field_type == "json" or "_steps" in field_name or "_process" in field_name:
                # Array type fields
                sample = f"""[
    {{"step": 1, "content": "步骤1的具体内容"}},
    {{"step": 2, "content": "步骤2的具体内容"}}
  ]"""
            elif field_type == "textarea" or "_analysis" in field_name or "_description" in field_name:
                # Long text fields
                hint = self._infer_field_hint(field_name)
                sample = f'"{hint}"'
            else:
                # Simple text fields
                hint = self._infer_field_hint(field_name)
                sample = f'"{hint}"'

            template_parts.append(f'  "{field_name}": {sample}')

        return "{\n" + ",\n".join(template_parts) + "\n}"

    def _build_field_generation_notes(self, field_configs: List[FieldConfig], generate_reflection: bool = False) -> str:
        """Build generation notes for custom fields."""
        notes = []

        # Add reflection to notes if generate_reflection is True
        if generate_reflection:
            notes.append("- reflection（教学反思）：对本节课教学效果的反思（至少2-3条）")

        custom_fields = [f for f in field_configs if f.name not in [
            "subject", "grade", "topic", "duration",
            "teaching_goals", "key_points", "difficult_points",
            "ideological_political",
            "teaching_tools", "teaching_methods", "student_analysis",
            "textbook_analysis", "teaching_steps", "homework",
            "blackboard_design", "reflection"
        ]]

        if custom_fields:
            notes.append("## 自定义字段说明")
            for field in custom_fields:
                display_name = field.display_name or field.name
                hint = self._infer_field_hint(field.name)
                notes.append(f"- {field.name} ({display_name}): {hint}")

        return "\n".join(notes) if notes else ""

    def _build_required_fields_note(self, field_configs: List[FieldConfig]) -> str:
        """Build a note emphasizing required fields."""
        if not field_configs:
            return ""

        # Filter required fields
        required_fields = [f for f in field_configs if f.required]

        if not required_fields:
            return ""

        # Build the note
        note = "## ⚠️ 必填字段要求\n\n"
        note += "以下字段为**必填字段**，必须全部生成，不得遗漏：\n\n"

        for idx, field in enumerate(required_fields, 1):
            display_name = field.display_name or field.name
            field_type_desc = {
                "text": "文本",
                "textarea": "长文本",
                "json": "结构化数据",
                "array": "数组"
            }.get(field.field_type, "内容")

            note += f"{idx}. **{field.name}** ({display_name}) - {field_type_desc}\n"

            # Add description if available
            if field.description:
                note += f"   - 说明：{field.description}\n"

            # Add special note for teaching_steps
            if field.name == "teaching_steps":
                note += f"   - **特别要求**：必须包含5个完整阶段（新课预热、问题导入、传授新知、课堂实践、课堂总结）；传授新知和课堂实践均为30分钟，并满足核心环节最低内容量\n"

        note += f"\n共 **{len(required_fields)}** 个必填字段，请确保每个字段都生成了有价值的具体内容。\n"
        note += "**严格要求**：\n"
        note += "- 不允许使用\"待补充\"、\"待填写\"、\"根据实际情况\"等占位符\n"
        note += "- 每个字段都必须提供详实、具体、可操作的内容\n"
        note += "- 所有字段内容应该相互关联、逻辑一致\n"

        return note

    def _infer_field_hint(self, field_name: str) -> str:
        """Infer generation hint from field name."""
        # Common patterns
        if "_name" in field_name or "_title" in field_name:
            return "根据上下文生成合适的名称"
        elif "_date" in field_name or "_time" in field_name:
            return "生成合适的日期或时间（可以留空或使用当前日期）"
        elif "school" in field_name:
            return "学校名称"
        elif "teacher" in field_name:
            return "教师姓名"
        elif "class" in field_name and "room" not in field_name:
            return "班级名称"
        elif "classroom" in field_name or "room" in field_name:
            return "教室或上课地点"
        elif "_analysis" in field_name:
            return "详细的分析内容（150-300字）"
        elif "_description" in field_name:
            return "详细的描述说明"
        elif "_objectives" in field_name or "_goals" in field_name:
            return "具体的目标列表"
        elif "_steps" in field_name or "_process" in field_name:
            return "分步骤的流程或过程"
        elif "_checklist" in field_name or "_list" in field_name:
            return "具体的清单项目"
        elif "_notes" in field_name or "_remarks" in field_name:
            return "相关注意事项或备注"
        elif "_materials" in field_name or "_resources" in field_name:
            return "所需材料或资源清单"
        else:
            # Use field name as hint
            return f"生成与'{field_name}'相关的适当内容"

    def _get_default_json_template(self, generate_reflection: bool = False) -> str:
        """Get the default JSON template for backward compatibility."""
        # Set reflection description based on parameter
        reflection_desc = (
            "对本节课教学效果的反思，包括成功之处、不足及改进措施（至少2-3条）"
            if generate_reflection
            else "（待课后填写）"
        )

        return """{{
  "teaching_goals": {{
    "knowledge": ["具体的知识目标1（至少2-3条）", "知识目标2"],
    "ability": ["具体的能力目标1（至少2-3条）", "能力目标2"],
    "quality": ["具体的素质目标1（至少2条）", "素质目标2"]
  }},
  "key_points": "教学重点内容，要具体明确",
  "difficult_points": "教学难点内容，说明难在哪里",
  "ideological_political": "结合本节课内容，挖掘课程思政元素，如：工匠精神、生态意识、家国情怀等",
  "teaching_tools": "教具和学具准备清单",
  "teaching_methods": "采用的教学方法",
  "student_analysis": "学情分析，包括认知基础、可能的困难",
  "textbook_analysis": "教材分析，说明本课在单元/教材中的地位",
  "teaching_steps": [
    {{
      "stage": "新课预热",
      "duration": "5分钟",
      "teacher_activity": "【教师】教师具体做什么、说什么",
      "student_activity": "【学生】学生具体做什么",
      "design_intent": "这样设计的教育目的"
    }},
    {{
      "stage": "问题导入",
      "duration": "5分钟",
      "teacher_activity": "【教师】...",
      "student_activity": "【学生】...",
      "design_intent": "..."
    }},
    {{
      "stage": "传授新知",
      "duration": "30分钟",
      "teacher_activity": "【教师】围绕核心原理、配置步骤、示范案例、易错点和验证方法进行完整讲解，不少于120个汉字",
      "student_activity": "【学生】按照任务单观察、记录、回答、同步操作并核对结果，不少于80个汉字",
      "design_intent": "建立原理、操作与验证证据之间的联系"
    }},
    {{
      "stage": "课堂实践",
      "duration": "30分钟",
      "teacher_activity": "【教师】发布分层任务，明确步骤、验收标准、故障排查方法并巡回指导，不少于80个汉字",
      "student_activity": "【学生】完成配置、排错、验证、证据留存、互评和改进，不少于120个汉字",
      "design_intent": "形成岗位实践、协作和质量验收能力"
    }},
    {{
      "stage": "课堂总结",
      "duration": "5分钟",
      "teacher_activity": "【教师】...",
      "student_activity": "【学生】...",
      "design_intent": "..."
    }}
  ],
  "homework": {{
    "required": "必做作业",
    "optional": "选做作业/拓展"
  }},
  "blackboard_design": "板书设计的文字描述或结构",
  "reflection": "{reflection_desc}",
  "online_resources": "与本课相关的网络资源链接，如在线课程、教学视频、参考资料网站等（提供2-4个有效的URL链接或资源名称）"
}}""".format(reflection_desc=reflection_desc)

    def _get_default_generation_notes(self, generate_reflection: bool = False) -> str:
        """Get default generation notes."""
        notes = """
- online_resources（网络资源）：与本课相关的网络资源链接，如在线课程、教学视频、参考资料网站等（提供2-4个有效的URL链接或资源名称）
"""
        if generate_reflection:
            notes += """
- reflection（教学反思）：对本节课教学效果的反思（至少2-3条）
"""
        return notes

    @classmethod
    def _normalize_teaching_steps(cls, data: Dict[str, Any]) -> None:
        """Normalize fixed-template stage names, durations, and role markers."""
        steps = data.get("teaching_steps")
        if not isinstance(steps, list):
            return

        for step in steps:
            if not isinstance(step, dict):
                continue
            stage = str(step.get("stage") or "").strip()
            stage = cls._STAGE_ALIASES.get(stage, stage)
            step["stage"] = stage
            if stage in cls._STAGE_DURATIONS:
                step["duration"] = cls._STAGE_DURATIONS[stage]

            for field_name, marker in (
                ("teacher_activity", "【教师】"),
                ("student_activity", "【学生】"),
            ):
                value = str(step.get(field_name) or "").strip()
                if value and not value.startswith(marker):
                    value = f"{marker}{value}"
                step[field_name] = value

    @classmethod
    def _validate_teaching_step_detail(cls, data: Dict[str, Any]) -> None:
        """Reject sparse core teaching stages so the AI retry can add detail."""
        steps = data.get("teaching_steps")
        if not isinstance(steps, list):
            raise ValueError("teaching_steps缺失，必须生成5个完整教学阶段")

        by_stage = {
            str(step.get("stage") or "").strip(): step
            for step in steps
            if isinstance(step, dict)
        }
        missing = [stage for stage in cls._STAGE_DURATIONS if stage not in by_stage]
        if missing:
            raise ValueError(f"缺少教学阶段：{'、'.join(missing)}")

        issues: list[str] = []
        for stage, field_rules in cls._CORE_STAGE_MIN_CHARS.items():
            step = by_stage[stage]
            for field_name, minimum in field_rules.items():
                value = str(step.get(field_name) or "")
                visible = re.sub(r"\s|【教师】|【学生】", "", value)
                if len(visible) < minimum:
                    label = "教师活动" if field_name == "teacher_activity" else "学生活动"
                    issues.append(f"{stage}{label}仅{len(visible)}字，至少需要{minimum}字")
        if issues:
            raise ValueError("；".join(issues))

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """
        Parse JSON from AI response with robust error handling.

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
                # Try to find JSON object directly (look for opening { and closing })
                start_idx = content.find('{')
                if start_idx != -1:
                    # Find matching closing brace
                    brace_count = 0
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
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                            if brace_count == 0:
                                content = content[start_idx:i + 1]
                                break

        # Parse JSON with multiple fallback attempts
        attempts = [
            # 1. Try parsing as-is
            lambda c: json.loads(c),
            # 2. Try parsing with relaxed control character handling
            lambda c: json.loads(c, strict=False),
            # 3. Try after removing trailing commas
            lambda c: json.loads(re.sub(r",\s*([}\]])", r"\1", c)),
            # 4. Try after fixing unquoted keys (only for simple cases)
            lambda c: json.loads(re.sub(r"(\w+)\s*:", r'"\1":', c)),
            # 5. Try after removing control characters
            lambda c: json.loads(re.sub(r'[\x00-\x1f\x7f-\x9f]', '', c)),
            # 6. Try after fixing comments (// style)
            lambda c: json.loads(re.sub(r'//.*?(\n|$)', '', c)),
            # 7. Try after adding missing commas between array items and object properties
            lambda c: json.loads(re.sub(r'([}\]])\s*\n\s*"', r'\1,\n  "', c)),
            lambda c: json.loads(re.sub(r'([}\]])\s*\n\s*(\d+)', r'\1,\n  \2', c)),
            lambda c: json.loads(re.sub(r'([}\]])\s*\n\s*\{', r'\1,\n  {', c)),
            lambda c: json.loads(re.sub(r'"([a-zA-Z_]+)"\s*\n\s*\{', r'"\1": {', c)),
            # 8. Try aggressive comma fixing (no newline)
            lambda c: json.loads(re.sub(r'([}\]])\s+"', r'\1, "', c)),
            lambda c: json.loads(re.sub(r'([}\]])\s+\{', r'\1, {', c)),
            lambda c: json.loads(re.sub(r'"(\w+)"\s+\{', r'"\1": {', c)),
            # 9. Try fixing multiline string issues
            lambda c: json.loads(re.sub(r'\n\s+', ' ', c)),
        ]

        last_error = None
        for attempt in attempts:
            try:
                result = attempt(content)
                # Validate the result has expected structure
                if isinstance(result, dict) and 'teaching_steps' in result:
                    return self._sanitize_control_chars(result)
                elif isinstance(result, dict):
                    return self._sanitize_control_chars(result)
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                continue

        # If all attempts failed, raise the last error
        raise ValueError(
            f"Failed to parse AI response as JSON. Last error: {last_error}\n"
            f"Content preview (first 500 chars): {content[:500]}..."
        )

    @staticmethod
    def _sanitize_control_chars(value: Any) -> Any:
        if isinstance(value, str):
            return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        if isinstance(value, list):
            return [AIGenerator._sanitize_control_chars(item) for item in value]
        if isinstance(value, dict):
            return {key: AIGenerator._sanitize_control_chars(val) for key, val in value.items()}
        return value

    @staticmethod
    def _clean_ai_response(content: str) -> str:
        if not content:
            return content
        cleaned = content.replace("\ufeff", "")
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned)
        return cleaned


async def generate_lesson_plan(
    input_data: LessonPlanInput,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    generate_reflection: bool = False,
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
    return await generator.generate_lesson_plan(input_data, generate_reflection=generate_reflection)
