"""
模板版本历史管理

保存模板的编辑历史，支持版本对比和回滚
"""
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from ..models.database import db


async def save_version(
    template_id: str,
    content: str,
    user: str = "系统",
    comment: str = ""
) -> str:
    """
    保存模板版本

    Args:
        template_id: 模板 ID
        content: HTML 内容
        user: 编辑用户
        comment: 版本说明

    Returns:
        版本 ID
    """
    # 生成版本 ID
    from ..models.schemas import generate_id
    version_id = generate_id()

    # 获取版本号
    row = await db.fetch_one(
        "SELECT MAX(version_number) as max_version FROM template_versions WHERE template_id = ?",
        (template_id,)
    )

    version_number = (row["max_version"] or 0) + 1 if row else 1

    # 保存版本
    await db.execute(
        """
        INSERT INTO template_versions
        (id, template_id, version_number, content, user, comment, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            template_id,
            version_number,
            content,
            user,
            comment,
            datetime.now().isoformat(),
        ),
        commit=True,
    )

    return version_id


async def get_versions(
    template_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Dict]:
    """
    获取模板的版本历史

    Args:
        template_id: 模板 ID
        limit: 限制数量
        offset: 偏移量

    Returns:
        版本列表
    """
    rows = await db.fetch_all(
        """
        SELECT id, version_number, user, comment, created_at,
               LENGTH(content) as content_size
        FROM template_versions
        WHERE template_id = ?
        ORDER BY version_number DESC
        LIMIT ? OFFSET ?
        """,
        (template_id, limit, offset),
    )

    versions = []
    for row in rows:
        versions.append({
            "id": row["id"],
            "version_number": row["version_number"],
            "user": row["user"],
            "comment": row["comment"],
            "created_at": row["created_at"],
            "content_size": row["content_size"],
        })

    return versions


async def get_version_content(version_id: str) -> Optional[str]:
    """
    获取指定版本的内容

    Args:
        version_id: 版本 ID

    Returns:
        HTML 内容
    """
    row = await db.fetch_one(
        "SELECT content FROM template_versions WHERE id = ?",
        (version_id,)
    )

    return row["content"] if row else None


async def compare_versions(
    version_id_1: str,
    version_id_2: str
) -> Dict:
    """
    对比两个版本

    Args:
        version_id_1: 版本 1 ID
        version_id_2: 版本 2 ID

    Returns:
        对比结果
    """
    # 获取两个版本的内容
    content_1 = await get_version_content(version_id_1)
    content_2 = await get_version_content(version_id_2)

    if not content_1 or not content_2:
        raise ValueError("版本不存在")

    # 简单的文本差异统计
    lines_1 = content_1.split('\n')
    lines_2 = content_2.split('\n')

    # 使用 difflib 进行对比
    import difflib
    diff = difflib.unified_diff(lines_1, lines_2, lineterm='')
    diff_text = '\n'.join(diff)

    # 统计变化
    added_lines = sum(1 for line in diff_text.split('\n') if line.startswith('+') and not line.startswith('+++'))
    removed_lines = sum(1 for line in diff_text.split('\n') if line.startswith('-') and not line.startswith('---'))

    return {
        "version_1": version_id_1,
        "version_2": version_id_2,
        "diff": diff_text,
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "total_changes": added_lines + removed_lines,
    }


async def restore_version(template_id: str, version_id: str) -> str:
    """
    恢复到指定版本

    Args:
        template_id: 模板 ID
        version_id: 要恢复的版本 ID

    Returns:
        新版本 ID
    """
    # 获取版本内容
    content = await get_version_content(version_id)

    if not content:
        raise ValueError("版本不存在")

    # 获取版本信息
    row = await db.fetch_one(
        "SELECT version_number FROM template_versions WHERE id = ?",
        (version_id,)
    )

    if not row:
        raise ValueError("版本不存在")

    # 保存为新版本
    new_version_id = await save_version(
        template_id=template_id,
        content=content,
        user="系统",
        comment=f"恢复到版本 {row['version_number']}"
    )

    return new_version_id


async def delete_old_versions(
    template_id: str,
    keep_count: int = 20
) -> int:
    """
    删除旧版本，只保留最新的 N 个版本

    Args:
        template_id: 模板 ID
        keep_count: 保留的版本数量

    Returns:
        删除的版本数
    """
    # 获取要删除的版本
    rows = await db.fetch_all(
        """
        SELECT id FROM template_versions
        WHERE template_id = ?
        ORDER BY version_number DESC
        LIMIT -1 OFFSET ?
        """,
        (template_id, keep_count),
    )

    if not rows:
        return 0

    # 删除
    version_ids = [row["id"] for row in rows]
    placeholders = ','.join('?' * len(version_ids))

    await db.execute(
        f"DELETE FROM template_versions WHERE id IN ({placeholders})",
        tuple(version_ids),
        commit=True,
    )

    return len(version_ids)


async def initialize_version_table():
    """初始化版本历史表"""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS template_versions (
            id TEXT PRIMARY KEY,
            template_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            user TEXT DEFAULT '系统',
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
        )
        """,
        commit=True,
    )

    # 创建索引
    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_template_versions_template_id
        ON template_versions(template_id)
        """,
        commit=True,
    )
