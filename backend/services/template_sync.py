"""
Template synchronization service.

自动扫描 storage/templates/ 文件夹中的模板文件，
并将不在数据库中的模板导入到数据库中。
"""
import logging
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any

from .template_parser import TemplateParser
from ..models.database import get_db
from ..config import settings

logger = logging.getLogger(__name__)


class TemplateSyncService:
    """模板同步服务 - 确保文件夹中的模板与数据库同步"""

    def __init__(self):
        self.template_dir = settings.template_dir

    async def sync_templates(self) -> Dict[str, int]:
        """
        同步模板文件夹到数据库

        Returns:
            包含同步统计的字典:
            - imported: 新导入的模板数量
            - skipped: 已存在跳过的模板数量
            - errors: 导入失败的模板数量
        """
        stats = {"imported": 0, "skipped": 0, "errors": 0}

        if not self.template_dir.exists():
            logger.warning(f"模板目录不存在: {self.template_dir}")
            return stats

        # 获取所有 .docx 文件
        docx_files = list(self.template_dir.glob("*.docx"))
        # 排除备份文件
        docx_files = [f for f in docx_files if not f.name.endswith(".backup")]

        if not docx_files:
            logger.info("模板文件夹中没有找到 .docx 文件")
            return stats

        # 获取数据库中已存在的模板路径
        db = await get_db()
        existing_templates = await db.fetch_all(
            "SELECT id, file_path FROM templates"
        )
        existing_paths = {row["file_path"] for row in existing_templates}

        logger.info(f"开始同步模板，找到 {len(docx_files)} 个文件")

        for template_file in docx_files:
            file_path = str(template_file)
            file_name = template_file.name

            # 检查是否已在数据库中
            if file_path in existing_paths:
                logger.debug(f"模板已存在，跳过: {file_name}")
                stats["skipped"] += 1
                continue

            # 导入新模板
            result = await self._import_template(template_file, db)
            if result == "success":
                stats["imported"] += 1
            elif result == "error":
                stats["errors"] += 1

        logger.info(
            f"模板同步完成: 导入={stats['imported']}, "
            f"跳过={stats['skipped']}, 错误={stats['errors']}"
        )

        return stats

    async def _import_template(
        self, template_file: Path, db: Any
    ) -> str:
        """
        导入单个模板到数据库

        Args:
            template_file: 模板文件路径
            db: 数据库实例

        Returns:
            "success" 或 "error"
        """
        file_path = str(template_file)
        file_name = template_file.name

        try:
            # 解析模板
            parser = TemplateParser(file_path)
            fields = parser.parse()

            # 验证模板
            is_valid, validation_errors = parser.validate_template()
            if not is_valid:
                logger.warning(
                    f"模板验证失败 ({file_name}): "
                    f"{' '.join(validation_errors)}"
                )
                return "error"

            # 使用文件名（不含扩展名）作为模板名称
            name = template_file.stem.replace("_", " ").replace("-", " ").strip()
            name = " ".join(word.capitalize() for word in name.split())

            # 生成唯一 ID
            template_id = str(uuid.uuid4())

            # 保存到数据库
            fields_config_json = json.dumps(
                [f.model_dump() for f in fields],
                ensure_ascii=False
            )

            await db.execute(
                """
                INSERT INTO templates (id, name, file_path, fields_config)
                VALUES (?, ?, ?, ?)
                """,
                (template_id, name, file_path, fields_config_json),
                commit=True,
            )

            logger.info(f"成功导入模板: {name} ({file_name})")
            return "success"

        except Exception as e:
            logger.error(f"导入模板失败 ({file_name}): {str(e)}")
            return "error"

    async def remove_deleted_templates(self) -> int:
        """
        清理数据库中已不存在的模板记录

        Returns:
            删除的记录数量
        """
        db = await get_db()

        # 获取数据库中的所有模板
        templates = await db.fetch_all("SELECT id, file_path FROM templates")

        deleted_count = 0
        for template in templates:
            file_path = Path(template["file_path"])
            if not file_path.exists():
                # 文件不存在，删除数据库记录
                await db.execute(
                    "DELETE FROM templates WHERE id = ?",
                    (template["id"],),
                    commit=True,
                )
                logger.info(f"清理已删除的模板: {template['file_path']}")
                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"清理了 {deleted_count} 个已删除的模板记录")

        return deleted_count


# 全局同步函数
async def sync_templates_on_startup() -> None:
    """
    应用启动时自动同步模板

    这个函数会在 FastAPI lifespan 中调用
    """
    service = TemplateSyncService()

    # 同步新模板
    await service.sync_templates()

    # 可选：清理已删除的模板记录
    # await service.remove_deleted_templates()
