# 教材管理功能部署指南

## 概述

本文档说明如何部署教材管理功能到现有的智能教案助手系统。

## 功能特性

- ✅ 教材CRUD管理（创建、读取、更新、删除）
- ✅ AI自动生成教材章节大纲
- ✅ 章节信息管理（章节编号、标题、概述、核心概念）
- ✅ 批量生成集成（选择教材自动加载章节）
- ✅ 单个生成集成（选择章节自动填充信息）
- ✅ 教材使用统计

## 数据库变更

### 新增表

系统会自动创建以下3个新表：

#### 1. `textbooks` - 教材主表
```sql
CREATE TABLE textbooks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    isbn TEXT,
    author TEXT,
    publisher TEXT,
    edition TEXT,
    subject TEXT,
    grade TEXT,
    cover_image TEXT,
    description TEXT,
    status TEXT DEFAULT 'active',
    use_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### 2. `textbook_chapters` - 教材章节表
```sql
CREATE TABLE textbook_chapters (
    id TEXT PRIMARY KEY,
    textbook_id TEXT NOT NULL,
    chapter_number TEXT NOT NULL,
    chapter_title TEXT NOT NULL,
    content_summary TEXT,
    key_concepts TEXT,
    sort_order INTEGER DEFAULT 0,
    hours_required INTEGER,
    parent_chapter_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (textbook_id) REFERENCES textbooks(id)
);
```

#### 3. `lesson_plan_textbooks` - 教案教材关联表
```sql
CREATE TABLE lesson_plan_textbooks (
    id TEXT PRIMARY KEY,
    lesson_plan_id TEXT NOT NULL,
    textbook_id TEXT NOT NULL,
    chapter_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (lesson_plan_id) REFERENCES lesson_plans(id),
    FOREIGN KEY (textbook_id) REFERENCES textbooks(id),
    FOREIGN KEY (chapter_id) REFERENCES textbook_chapters(id)
);
```

### 数据库迁移

**重要提示**：数据库表会在后端启动时自动创建，无需手动执行SQL脚本。

系统使用 `backend/models/database.py` 中的 `_create_tables()` 函数自动创建所有表。

## 部署步骤

### 1. 备份现有数据

```bash
# 备份数据库
cp storage/database.db storage/database.db.backup.$(date +%Y%m%d_%H%M%S)
```

### 2. 更新代码

确保所有新文件已经部署到服务器：

**后端新增文件**：
- `backend/services/textbook_generator.py` - AI章节生成服务
- `backend/api/textbooks.py` - 教材API端点

**前端新增文件**：
- `frontend/src/services/textbookApi.ts` - 教材API客户端
- `frontend/src/stores/textbookStore.ts` - 教材状态管理
- `frontend/src/pages/TextbookManager.tsx` - 教材管理页面

**修改的文件**：
- `backend/models/schemas.py` - 添加教材相关模型
- `backend/models/database.py` - 添加表创建逻辑
- `backend/main.py` - 注册教材路由
- `frontend/src/types/index.ts` - 添加教材类型定义
- `frontend/src/pages/BatchGenerate.tsx` - 集成教材选择
- `frontend/src/pages/NewLessonPlan.tsx` - 集成教材选择
- `frontend/src/App.tsx` - 添加教材管理路由
- `frontend/src/pages/Home.tsx` - 添加教材管理入口

### 3. 重启后端服务

```bash
# 停止现有服务
./stop.sh  # Linux/Mac
# 或
stop.bat   # Windows

# 启动服务（数据库表会自动创建）
./start.sh  # Linux/Mac
# 或
start.bat   # Windows
```

### 4. 重新构建前端

```bash
cd frontend
npm install  # 安装可能的新依赖
npm run build
```

### 5. 验证部署

运行测试脚本验证API功能：

```bash
# 确保后端服务已启动
python test_textbook_api.py
```

预期输出：
- ✓ Created textbook
- ✓ Retrieved textbooks
- ✓ Generated chapters (AI)
- ✓ Saved chapters
- ✓ Verified chapters saved

## 功能测试清单

### 1. 教材管理页面测试

访问 `http://localhost:5173/textbooks` 验证：

- [ ] 页面正常加载，显示教材列表
- [ ] 可以创建新教材（点击"新建教材"按钮）
- [ ] 可以编辑现有教材
- [ ] 可以删除教材（软删除）
- [ ] 学科和年级筛选功能正常
- [ ] 分页功能正常

### 2. AI章节生成测试

在教材管理页面：

- [ ] 创建教材后提示"生成章节？"
- [ ] 点击"生成章节"打开AI生成对话框
- [ ] AI成功生成章节列表（10-30秒）
- [ ] 可以在预览中编辑章节信息
- [ ] 点击"保存章节"成功保存
- [ ] 查看章节显示已保存的章节

### 3. 批量生成集成测试

访问 `http://localhost:5173/batch-generate` 验证：

- [ ] "课程基本信息"卡片中显示"选择教材"下拉框
- [ ] 选择教材后自动填充课程名称、学科、年级
- [ ] 显示"已加载 X 个教材章节"标签
- [ ] 可以直接进入第2步查看章节
- [ ] 章节信息正确显示（课题、内容概述、核心概念）
- [ ] 可以正常生成批量教案

### 4. 单个生成集成测试

访问 `http://localhost:5173/new` 验证：

- [ ] Step 2 "教学设置"中显示"选择教材"下拉框
- [ ] 选择教材后显示"选择章节"下拉框
- [ ] 选择章节后自动填充：
  - 课题 = 章节标题
  - 单元名称 = 章节编号 + 标题
  - 学生已有知识 = 章节概述 + 核心概念
- [ ] 可以继续编辑自动填充的内容
- [ ] 可以正常生成教案

## 注意事项

### 1. AI配置要求

教材章节生成功能需要AI服务正常运行：

- 确保 `.env` 文件中配置了有效的 `DEEPSEEK_API_KEY` 或 `ANTHROPIC_API_KEY`
- AI生成章节通常需要10-30秒，请耐心等待
- 如果AI服务不可用，可以手动创建教材但无法使用AI生成章节

### 2. 数据兼容性

- 新功能完全向后兼容，不影响现有教案生成流程
- 教材选择是可选的，用户可以继续使用原有方式
- 现有教案数据不受影响

### 3. 性能考虑

- 教材列表支持分页（默认20条/页）
- 章节数量建议控制在50个以内
- AI生成章节时会消耗API配额

### 4. 回滚方案

如果需要回滚：

```bash
# 1. 恢复数据库备份
cp storage/database.db.backup.YYYYMMDD_HHMMSS storage/database.db

# 2. 回滚代码到之前的版本
git checkout <previous-commit>

# 3. 重启服务
./stop.sh && ./start.sh
```

## 技术支持

如遇到问题，请检查：

1. **后端日志**：查看 `backend/logs/` 或控制台输出
2. **前端控制台**：浏览器开发者工具 Console 标签
3. **数据库状态**：使用 SQLite 工具查看表结构
4. **API测试**：访问 `http://127.0.0.1:8000/docs` 查看Swagger文档

## 总结

教材管理功能已完整集成到系统中，提供了：

✅ **完整的教材管理** - CRUD操作、AI章节生成、章节编辑
✅ **批量生成集成** - 选择教材快速创建整学期教案
✅ **单个生成集成** - 选择章节自动填充教案信息
✅ **向后兼容** - 不影响现有功能和数据
✅ **测试脚本** - 自动化API测试验证

部署完成后，用户可以：
1. 在教材管理页面创建和管理教材
2. 使用AI自动生成教材章节大纲
3. 在批量生成时选择教材快速创建教案
4. 在单个生成时选择章节自动填充信息

---

**部署日期**: _____________
**部署人员**: _____________
**验证状态**: [ ] 通过 [ ] 未通过
**备注**: _____________
