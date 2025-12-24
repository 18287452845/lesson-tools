"""
Jinja2 语法保护模块

用于在 HTML 编辑过程中保护 Jinja2 模板语法不被破坏。
将 {{variable}} 和 {% tag %} 等语法转换为 HTML 安全的格式。
"""
import re
import uuid
from typing import Dict, List, Tuple


class JinjaProtector:
    """Jinja2 语法保护器"""

    # Jinja2 语法正则模式
    VARIABLE_PATTERN = r'\{\{[^}]+\}\}'  # 匹配 {{variable}}
    BLOCK_PATTERN = r'\{%[^%]+%\}'       # 匹配 {% for %}, {% if %} 等
    COMMENT_PATTERN = r'\{#[^#]+#\}'     # 匹配 {# comment #}

    def __init__(self):
        self.placeholders: Dict[str, str] = {}  # 存储占位符映射

    def protect(self, text: str) -> str:
        """
        保护 Jinja2 语法，将其转换为 HTML 安全的格式

        Args:
            text: 包含 Jinja2 语法的文本

        Returns:
            保护后的 HTML 文本
        """
        # 先匹配变量
        text = self._protect_variables(text)
        # 再匹配块标签
        text = self._protect_blocks(text)
        # 最后匹配注释
        text = self._protect_comments(text)

        return text

    def restore(self, html: str) -> str:
        """
        从 HTML 中恢复 Jinja2 语法

        Args:
            html: 包含保护标记的 HTML

        Returns:
            恢复后的文本，包含原始 Jinja2 语法
        """
        # 从 data-jinja 属性恢复
        pattern = r'<span[^>]*data-jinja="([^"]+)"[^>]*>.*?</span>'

        def replacer(match):
            jinja_code = match.group(1)
            # 解码 HTML 实体
            jinja_code = jinja_code.replace('&lt;', '<').replace('&gt;', '>')
            jinja_code = jinja_code.replace('&#123;', '{').replace('&#125;', '}')
            jinja_code = jinja_code.replace('&quot;', '"').replace('&#39;', "'")
            return jinja_code

        return re.sub(pattern, replacer, html)

    def _protect_variables(self, text: str) -> str:
        """保护 Jinja2 变量"""
        def replacer(match):
            jinja = match.group(0)
            # 生成唯一ID
            unique_id = f"jinja-var-{uuid.uuid4().hex[:8]}"
            # 转换为安全的 HTML
            safe_jinja = self._html_escape(jinja)
            return (
                f'<span class="jinja-placeholder jinja-variable" '
                f'data-jinja="{safe_jinja}" '
                f'data-type="variable" '
                f'id="{unique_id}" '
                f'contenteditable="false">'
                f'{jinja}'
                f'</span>'
            )

        return re.sub(self.VARIABLE_PATTERN, replacer, text)

    def _protect_blocks(self, text: str) -> str:
        """保护 Jinja2 块标签"""
        def replacer(match):
            jinja = match.group(0)
            # 判断是开始标签还是结束标签
            block_type = self._get_block_type(jinja)
            unique_id = f"jinja-block-{uuid.uuid4().hex[:8]}"
            safe_jinja = self._html_escape(jinja)

            return (
                f'<span class="jinja-placeholder jinja-block" '
                f'data-jinja="{safe_jinja}" '
                f'data-type="block" '
                f'data-block-type="{block_type}" '
                f'id="{unique_id}" '
                f'contenteditable="false">'
                f'{jinja}'
                f'</span>'
            )

        return re.sub(self.BLOCK_PATTERN, replacer, text)

    def _protect_comments(self, text: str) -> str:
        """保护 Jinja2 注释"""
        def replacer(match):
            jinja = match.group(0)
            unique_id = f"jinja-comment-{uuid.uuid4().hex[:8]}"
            safe_jinja = self._html_escape(jinja)

            return (
                f'<span class="jinja-placeholder jinja-comment" '
                f'data-jinja="{safe_jinja}" '
                f'data-type="comment" '
                f'id="{unique_id}" '
                f'contenteditable="false" '
                f'style="display:none;">'
                f'{jinja}'
                f'</span>'
            )

        return re.sub(self.COMMENT_PATTERN, replacer, text)

    def _get_block_type(self, block_tag: str) -> str:
        """获取块标签类型"""
        if 'for' in block_tag:
            return 'for-start' if 'endfor' not in block_tag else 'for-end'
        elif 'if' in block_tag:
            return 'if-start' if 'endif' not in block_tag else 'if-end'
        elif 'elif' in block_tag:
            return 'elif'
        elif 'else' in block_tag:
            return 'else'
        else:
            return 'unknown'

    def _html_escape(self, text: str) -> str:
        """HTML 转义"""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#39;')
                    .replace('{', '&#123;')
                    .replace('}', '&#125;'))

    def validate_jinja_syntax(self, text: str) -> Tuple[bool, List[str]]:
        """
        验证 Jinja2 语法是否正确

        Args:
            text: 要验证的文本

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 检查变量语法
        var_pattern = r'\{\{([^}]+)\}\}'
        for match in re.finditer(var_pattern, text):
            var_content = match.group(1).strip()
            if not var_content:
                errors.append(f"空变量: {match.group(0)}")

        # 检查块标签配对
        block_stack = []
        block_pattern = r'\{%\s*(\w+)[^%]*%\}'

        for match in re.finditer(block_pattern, text):
            tag = match.group(1)

            if tag in ['for', 'if', 'block']:
                block_stack.append((tag, match.start()))
            elif tag in ['endfor', 'endif', 'endblock']:
                expected = tag[3:]  # 去掉 'end' 前缀
                if not block_stack:
                    errors.append(f"未匹配的结束标签: {match.group(0)}")
                else:
                    start_tag, _ = block_stack.pop()
                    if start_tag != expected:
                        errors.append(
                            f"标签不匹配: 期望 end{start_tag}，找到 {match.group(0)}"
                        )

        # 检查未闭合的块
        for tag, pos in block_stack:
            errors.append(f"未闭合的 {tag} 标签（位置 {pos}）")

        return len(errors) == 0, errors

    def extract_jinja_fields(self, text: str) -> List[str]:
        """
        提取文本中的所有 Jinja2 变量名

        Args:
            text: 包含 Jinja2 语法的文本

        Returns:
            变量名列表
        """
        fields = set()

        # 提取简单变量
        var_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
        fields.update(re.findall(var_pattern, text))

        # 提取对象属性（如 teaching_goals.knowledge）
        obj_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\}\}'
        for match in re.finditer(obj_pattern, text):
            # 只取第一部分（对象名）
            field = match.group(1).split('.')[0]
            fields.add(field)

        # 提取循环变量
        for_pattern = r'\{%\s*for\s+\w+\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}'
        fields.update(re.findall(for_pattern, text))

        return sorted(list(fields))


# 便捷函数
def protect_jinja_syntax(text: str) -> str:
    """保护 Jinja2 语法"""
    protector = JinjaProtector()
    return protector.protect(text)


def restore_jinja_syntax(html: str) -> str:
    """恢复 Jinja2 语法"""
    protector = JinjaProtector()
    return protector.restore(html)


def validate_jinja(text: str) -> Tuple[bool, List[str]]:
    """验证 Jinja2 语法"""
    protector = JinjaProtector()
    return protector.validate_jinja_syntax(text)


def extract_jinja_variables(text: str) -> List[str]:
    """提取 Jinja2 变量"""
    protector = JinjaProtector()
    return protector.extract_jinja_fields(text)
