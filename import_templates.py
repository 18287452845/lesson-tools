"""
导入 storage/templates/ 文件夹中的现有模板到数据库

运行方式：
    python import_templates.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.models.database import get_db
from backend.services.template_parser import TemplateParser
import json


async def import_existing_templates():
    """扫描 templates 文件夹并导入现有模板到数据库"""
    db = await get_db()
    template_dir = Path("storage/templates")

    if not template_dir.exists():
        print(f"模板目录不存在: {template_dir}")
        return

    # 获取所有 .docx 文件
    docx_files = list(template_dir.glob("*.docx"))
    # 排除备份文件
    docx_files = [f for f in docx_files if not f.name.endswith(".backup")]

    if not docx_files:
        print("没有找到 .docx 模板文件")
        return

    print(f"找到 {len(docx_files)} 个模板文件:")
    print()

    # 检查数据库中已存在的模板
    existing_templates = await db.fetch_all("SELECT id, name, file_path FROM templates")
    existing_paths = {row["file_path"]: row["id"] for row in existing_templates}

    imported = 0
    skipped = 0
    errors = 0

    for template_file in docx_files:
        file_path = str(template_file)
        file_name = template_file.name

        print(f"处理: {file_name}")

        # 检查是否已在数据库中
        if file_path in existing_paths:
            print(f"  ⏭ 已存在数据库中，跳过")
            skipped += 1
            continue

        try:
            # 解析模板
            parser = TemplateParser(file_path)
            fields = parser.parse()

            # 验证模板
            is_valid, validation_errors = parser.validate_template()
            if not is_valid:
                print(f"  ❌ 模板验证失败: {'; '.join(validation_errors)}")
                errors += 1
                continue

            # 使用文件名（不含扩展名）作为模板名称
            name = template_file.stem.replace("_", " ").title()

            # 生成唯一 ID
            import uuid
            template_id = str(uuid.uuid4())

            # 保存到数据库
            fields_config_json = json.dumps([f.model_dump() for f in fields])

            await db.execute(
                """
                INSERT INTO templates (id, name, file_path, fields_config)
                VALUES (?, ?, ?, ?)
                """,
                (template_id, name, file_path, fields_config_json),
                commit=True,
            )

            print(f"  ✅ 导入成功 (ID: {template_id})")
            print(f"     字段: {len(fields)} 个")
            imported += 1

        except Exception as e:
            print(f"  ❌ 导入失败: {str(e)}")
            errors += 1

        print()

    # 显示总结
    print("=" * 50)
    print("导入完成!")
    print(f"  导入: {imported} 个")
    print(f"  跳过: {skipped} 个")
    print(f"  失败: {errors} 个")
    print("=" * 50)

    # 显示数据库中的所有模板
    print("\n数据库中的所有模板:")
    all_templates = await db.fetch_all("SELECT id, name, file_path FROM templates")
    for row in all_templates:
        print(f"  - [{row['id'][:8]}] {row['name']}")


if __name__ == "__main__":
    asyncio.run(import_existing_templates())
