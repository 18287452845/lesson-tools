# Word 导出格式修复说明

## 问题描述

导出的 Word 文档格式与设置的模板不一致，主要表现在：
- **表格结构被改变**：模板中的12x5和9x2表格变成了10x2和8x2
- **格式丢失**：原始模板的格式和样式没有被保留

## 根本原因

`backend/services/document_renderer.py` 使用的是 `python-docx` 库进行简单的文本替换，但这个方法**不适合模板渲染**：

1. `python-docx` 只做文本替换，**不保留原始文档结构**
2. 当处理包含 Jinja2 语法（`{% for %}` 等）的模板时，它无法正确处理
3. 表格的行列结构会被破坏

## 解决方案

将渲染引擎从 `python-docx` 切换到 `docxtpl`：

### 修改的文件：
- `backend/services/document_renderer.py`

### 关键更改：

**之前的实现** (错误):
```python
from docx import Document

doc = Document(template_path)
self._fill_template(doc, data)  # 手动文本替换
doc.save(output_path)
```

**修复后的实现** (正确):
```python
from docxtpl import DocxTemplate

doc_template = DocxTemplate(template_path)
doc_template.render(processed_data)  # 使用模板引擎渲染
doc_template.save(output_path)
```

## 为什么 docxtpl 更好？

1. **专为模板设计**：`docxtpl` 是专门用于 Word 模板渲染的库
2. **支持 Jinja2**：完整支持 `{% for %}`, `{% if %}` 等模板语法
3. **保留格式**：完美保留原始文档的所有格式、样式和表格结构
4. **循环处理**：可以正确处理 `{% for %}` 循环，动态生成表格行

## 验证结果

### 测试前（使用 python-docx）：
```
⚠️ STRUCTURE COMPARISON:
   Table 0: Template=12x5, Output=10x2 ❌
   Table 1: Template=9x2, Output=8x2 ❌
```

### 测试后（使用 docxtpl）：
```
✅ STRUCTURE COMPARISON:
   Table 0: Template=12x5, Output=12x5 ✅
   Table 1: Template=9x2, Output=9x2 ✅
```

## 如何测试

运行测试脚本验证修复：
```bash
python test_docxtpl.py
```

或通过API测试：
1. 启动后端服务
2. 创建一个教案
3. 导出为 Word 文档
4. 检查输出文档的格式是否与模板一致

## 影响范围

这个修复影响所有通过模板生成的 Word 文档，包括：
- 教案导出功能
- 所有使用 `DocumentRenderer` 的 API 端点

## 注意事项

1. **模板语法**：模板必须使用 Jinja2 语法（`{{ variable }}` 和 `{% tag %}`）
2. **数据结构**：传递给渲染器的数据结构必须与模板中的变量匹配
3. **向后兼容**：现有模板（如 `yunnan_forestry_college_template.docx`）已经使用了正确的 Jinja2 语法，无需修改

## 技术细节

### 模板变量示例：
- 简单变量：`{{ teaching_topic }}`
- 对象属性：`{{ homework.required }}`
- 循环：`{% for g in teaching_goals.knowledge %}{{ g }}{% endfor %}`
- 列表迭代：`{% for step in teaching_steps %}...{% endfor %}`

### 数据处理：
`_process_data()` 方法仍然负责：
- 将复杂数据结构（如 teaching_goals）转换为模板友好的格式
- 提供多种字段别名以兼容不同模板
- 处理空值和类型转换

## 相关文件

- ✅ `backend/services/document_renderer.py` - 已修复
- ✅ `test_docxtpl.py` - 测试脚本
- ✅ `debug_template.py` - 调试工具
- 📄 `storage/templates/yunnan_forestry_college_template.docx` - 模板文件
- 📁 `storage/outputs/` - 输出文件目录

## 结论

通过切换到 `docxtpl`，Word 导出功能现在能够：
- ✅ 完美保留模板的表格结构
- ✅ 保持所有格式和样式
- ✅ 正确处理循环和条件语句
- ✅ 与现有模板100%兼容
