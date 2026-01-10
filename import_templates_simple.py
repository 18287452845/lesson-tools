"""
简单的模板导入脚本 - 直接操作数据库
"""
import sqlite3
import uuid
from pathlib import Path

def import_templates():
    """导入模板文件到数据库"""
    db_path = "storage/database.db"
    template_dir = Path("storage/templates")

    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=== 开始导入模板 ===\n")

    # 获取所有 .docx 文件
    template_files = list(template_dir.glob("*.docx"))
    template_files = [f for f in template_files if not f.name.endswith(".backup")]

    print(f"找到 {len(template_files)} 个模板文件\n")

    imported = 0
    for template_file in template_files:
        file_path = str(template_file)
        file_name = template_file.name

        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM templates WHERE file_path = ?",
            (file_path,)
        )
        existing = cursor.fetchone()

        if existing:
            print(f"跳过（已存在）: {file_name}")
            continue

        # 生成模板名称（美化文件名）
        name = template_file.stem.replace("_", " ").replace("-", " ").strip()
        name = " ".join(word.capitalize() for word in name.split())

        # 生成唯一 ID
        template_id = str(uuid.uuid4())

        # 插入数据库（使用基本字段配置）
        cursor.execute(
            """
            INSERT INTO templates (id, name, file_path, fields_config)
            VALUES (?, ?, ?, ?)
            """,
            (template_id, name, file_path, "[]")  # 空字段配置
        )

        print(f"✓ 导入成功: {name}")
        print(f"  文件: {file_name}")
        print(f"  路径: {file_path}")
        print()

        imported += 1

    # 提交更改
    conn.commit()

    print(f"=== 导入完成 ===")
    print(f"成功导入 {imported} 个模板\n")

    # 显示当前所有模板
    cursor.execute("SELECT id, name, file_path FROM templates")
    templates = cursor.fetchall()

    print(f"数据库中共有 {len(templates)} 条模板记录:")
    for t in templates:
        print(f"  - {t[1]}")
        print(f"    路径: {t[2]}")
        print()

    conn.close()

if __name__ == "__main__":
    import_templates()
