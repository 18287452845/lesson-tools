"""
模板验证调试工具
"""
import sys
from pathlib import Path

# Add project root to path (cross-platform)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.services.template_parser import TemplateParser


def debug_template(template_path: str):
    """调试模板，显示所有发现的标签"""
    print(f"=== 模板分析: {template_path} ===\n")

    parser = TemplateParser(template_path)

    # 解析字段
    try:
        fields = parser.parse()

        print(f"发现 {len(fields)} 个字段:\n")

        # 按类型分组显示
        simple_fields = [f for f in parser.fields if f.field_type == "simple"]
        loop_fields = [f for f in parser.fields if f.field_type == "loop_start"]
        conditional_fields = [f for f in parser.fields if f.field_type == "conditional"]

        print(f"简单变量 ({len(simple_fields)}):")
        for f in simple_fields:
            print(f"  - {f.name}")

        print(f"\n循环标签 ({len(loop_fields)}):")
        for f in loop_fields:
            print(f"  - for {f.loop_variable} in {f.name}")

        if conditional_fields:
            print(f"\n条件标签 ({len(conditional_fields)}):")
            for f in conditional_fields:
                print(f"  - {f.raw_placeholder}")

        # 验证
        is_valid, errors = parser.validate_template()

        print(f"\n=== 验证结果: {'[PASS]' if is_valid else '[FAIL]'} ===")
        if errors:
            print("\n错误:")
            for error in errors:
                print(f"  - {error}")

        return is_valid

    except Exception as e:
        # Use ASCII-safe output for Windows console
        print(f"[ERROR] Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 默认调试 yunnan_forestry_college_template.docx
    template = "storage/templates/yunnan_forestry_college_template.docx"

    # 可以指定其他模板
    if len(sys.argv) > 1:
        template = sys.argv[1]

    debug_template(template)
