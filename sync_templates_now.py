"""
手动同步模板到数据库
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.template_sync import TemplateSyncService

async def main():
    """运行模板同步"""
    print("=== 开始同步模板 ===\n")

    service = TemplateSyncService()

    # 同步模板
    stats = await service.sync_templates()

    print(f"\n=== 同步完成 ===")
    print(f"新导入: {stats['imported']} 个")
    print(f"已跳过: {stats['skipped']} 个")
    print(f"错误: {stats['errors']} 个")

    # 可选：清理已删除的模板
    deleted = await service.remove_deleted_templates()
    if deleted > 0:
        print(f"清理已删除: {deleted} 个")

if __name__ == "__main__":
    asyncio.run(main())
