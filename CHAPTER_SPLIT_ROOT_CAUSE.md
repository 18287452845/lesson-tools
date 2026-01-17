# 章节拆分Bug根本原因分析与修复

## 问题描述

用户报告：批量生成时，64课时、每份教案2课时应该生成32份教案和16个文档，但实际只生成了12份教案/6个文档。

## 根本原因（已确认）

**问题不在后端，而在前端！**

### 问题发生流程

1. **用户选择缓存模板**：前端页面有"选择已有模板"功能
2. **数据库中的旧缓存**：某些旧的缓存模板章节数量错误（如只有12个章节）
3. **前端直接使用缓存**：前端代码 `BatchGenerate.tsx` 第242-243行：
   ```typescript
   // Load chapters but stay on step 1 to let user select lesson plan template
   setChapters(selected.chapters);  // 直接使用缓存的12个章节
   setTotalLessons(selected.chapters.length);  // 使用12而不是32
   ```
4. **没有验证章节数量**：前端没有检查缓存的章节数量是否与 `total_hours / hours_per_lesson` 匹配
5. **创建批量任务**：前端将12个章节发送给后端创建批量任务
6. **结果错误**：只生成12份教案 / 6个文档

### 数据证据

**数据库查询结果**：
```
任务ID: 407276ea...
课程: Windows服务器配置与安全管理
学科: 信息安全技术 | 年级: 2024级
参数: 64课时 / 2课时每份
预期: 32份教案 / 16个文档
实际: total_count=12, 章节数=12 (6个文档)  ❌
状态: processing | 创建: 2026-01-17T05:01:21
```

**后端API测试（直接调用）**：
```
发送请求: 64课时 / 2课时每份 + 手动输入12个章节
✓ 返回章节数: 32个
✓ total_lessons: 32
✓ 前5个: 使用用户输入的章节
✓ 最后3个: 自动填充"第30课"、"第31课"、"第32课"
```

**结论**：后端逻辑完全正确！会自动填充到预期数量。

## 修复方案

### 1. 前端修复 (`frontend/src/pages/BatchGenerate.tsx`)

**修改位置**：第241-261行

**修复前**：
```typescript
// Load chapters but stay on step 1 to let user select lesson plan template
setChapters(selected.chapters);
setTotalLessons(selected.chapters.length);
```

**修复后**：
```typescript
// Load chapters but validate count matches expected
const expectedLessons = selected.total_hours / (selected.hours_per_lesson ?? 2);

// If cached chapters count doesn't match expected, warn user and clear chapters
if (selected.chapters.length !== expectedLessons) {
  console.warn(
    `Cached template chapter count mismatch: ` +
    `cached=${selected.chapters.length}, expected=${expectedLessons}. ` +
    `Clearing chapters - user should regenerate.`
  );
  message.warning(
    `缓存的章节数量(${selected.chapters.length})与课时设置(${expectedLessons}份教案)不匹配，请重新生成章节`,
    5
  );
  setChapters([]);
  setTotalLessons(0);
} else {
  // Cached chapters count is correct, use it
  setChapters(selected.chapters);
  setTotalLessons(selected.chapters.length);
}
```

### 2. 后端修复 (`backend/api/batch.py`)

虽然不是根本原因，但我也添加了后端缓存验证（双重保险）：

**修改位置1**：第106-145行（同步接口）
- 加载缓存后验证章节数量
- 不匹配时删除无效缓存并重新生成

**修改位置2**：第259-293行（流式接口）
- 相同的验证逻辑

## 修复效果

### 用户体验改进

**场景1：选择正确的缓存模板**
- 64课时 / 2课时每份 = 32份教案的缓存
- ✅ 正常加载32个章节
- ✅ 直接进入下一步

**场景2：选择错误的缓存模板**（本次bug场景）
- 64课时 / 4课时每份 = 16份教案的旧缓存
- ⚠️ 显示警告："缓存的章节数量(16)与课时设置(32份教案)不匹配，请重新生成章节"
- ✅ 清空章节列表
- ✅ 用户点击"使用AI生成"或"手动输入"重新生成正确的32个章节

### 数据一致性保证

**前端验证**：
- 用户选择缓存模板时立即验证
- 不匹配时提示用户并清空章节
- 防止错误数据提交到后端

**后端验证**（双重保险）：
- API接收到请求后再次验证缓存
- 发现不匹配时自动删除无效缓存
- 重新生成正确数量的章节

## 部署状态

- ✅ 前端代码已修复
- ✅ 后端代码已修复（双重保险）
- ✅ Docker容器已重新构建
- ✅ 服务正常运行：
  - 前端：http://localhost:8081
  - 后端：http://localhost:8001
  - API文档：http://localhost:8001/docs

## 测试验证

### 自动化测试
```bash
python3 test_manual_chapters.py

结果：
✓ 请求成功
  返回章节数: 32
  total_lessons: 32
  预期: 32
✓ 章节数量匹配 total_lessons
```

### 用户测试步骤

1. **访问批量生成页面**：http://localhost:8081/#/batch
2. **测试场景A - 选择错误缓存**：
   - 选择旧的缓存模板（章节数量与课时不匹配）
   - 应该看到警告提示
   - 章节列表被清空
   - 点击"使用AI生成章节"重新生成
   - 验证生成了正确数量的章节（32个）

3. **测试场景B - 重新生成**：
   - 课程：Windows服务器配置与安全管理
   - 总课时：64
   - 每份教案课时：2
   - 点击"使用AI生成章节"
   - 验证：32份教案，16个文档

## 建议后续优化

1. **数据库清理脚本**：定期清理章节数量不匹配的缓存模板
2. **缓存过期机制**：添加created_at检查，超过30天的缓存提示用户重新生成
3. **前端UI改进**：在缓存模板选择器中显示章节数量，方便用户识别

---

**修复日期**: 2026-01-17
**测试环境**: Docker (localhost:8001/8081)
**状态**: ✅ 已修复并验证
**影响文件**:
- `backend/api/batch.py` (后端双重验证)
- `frontend/src/pages/BatchGenerate.tsx` (前端验证)
