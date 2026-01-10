"""
修复数据库中模板文件路径的脚本

功能：
1. 将 Windows 路径格式转换为跨平台格式
2. 删除重复的模板记录
3. 确保路径与实际文件匹配
"""
import sqlite3
import os
from pathlib import Path

def fix_template_paths():
    """修复数据库中的模板路径"""
    db_path = "storage/database.db"
    template_dir = Path("storage/templates")

    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=== 开始修复模板路径 ===\n")

    # 1. 获取所有模板记录
    cursor.execute("SELECT id, name, file_path FROM templates")
    templates = cursor.fetchall()

    print(f"找到 {len(templates)} 条模板记录")

    # 2. 获取实际存在的模板文件
    actual_files = list(template_dir.glob("*.docx"))
    actual_files = [f for f in actual_files if not f.name.endswith(".backup")]

    print(f"找到 {len(actual_files)} 个实际模板文件")
    print("实际文件列表:")
    for f in actual_files:
        print(f"  - {f}")
    print()

    # 3. 构建文件名到完整路径的映射
    file_map = {f.name: str(f) for f in actual_files}

    # 4. 检查每条记录
    to_delete = []
    to_update = []
    seen_files = set()

    for template in templates:
        template_id = template["id"]
        name = template["name"]
        old_path = template["file_path"]

        # 从路径中提取文件名（处理 Windows 和 Linux 路径格式）
        # 替换 Windows 路径分隔符为 Linux 路径分隔符
        normalized_path = old_path.replace("\\", "/")
        file_name = Path(normalized_path).name

        print(f"检查记录: {name}")
        print(f"  当前路径: {old_path}")
        print(f"  文件名: {file_name}")

        # 检查文件是否存在
        if file_name not in file_map:
            print(f"  ❌ 文件不存在，将删除此记录")
            to_delete.append(template_id)
        elif file_name in seen_files:
            print(f"  ❌ 重复记录，将删除")
            to_delete.append(template_id)
        else:
            # 文件存在且不是重复记录
            correct_path = file_map[file_name]
            if old_path != correct_path:
                print(f"  ✓ 需要更新路径为: {correct_path}")
                to_update.append((template_id, correct_path))
            else:
                print(f"  ✓ 路径正确，无需修改")
            seen_files.add(file_name)

        print()

    # 5. 执行删除操作
    if to_delete:
        print(f"\n=== 删除 {len(to_delete)} 条记录 ===")
        for template_id in to_delete:
            cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            print(f"已删除: {template_id}")
        conn.commit()

    # 6. 执行更新操作
    if to_update:
        print(f"\n=== 更新 {len(to_update)} 条记录的路径 ===")
        for template_id, new_path in to_update:
            cursor.execute(
                "UPDATE templates SET file_path = ? WHERE id = ?",
                (new_path, template_id)
            )
            print(f"已更新: {template_id} -> {new_path}")
        conn.commit()

    # 7. 显示修复后的结果
    print("\n=== 修复完成 ===")
    cursor.execute("SELECT id, name, file_path FROM templates")
    templates = cursor.fetchall()

    print(f"\n当前数据库中有 {len(templates)} 条模板记录:")
    for t in templates:
        print(f"  - {t['name']}: {t['file_path']}")

    conn.close()

    print("\n✓ 路径修复完成!")

if __name__ == "__main__":
    fix_template_paths()
