# 云林智能备课工作台

面向教师的一体化备课工具。一次填写课程信息，即可按需生成：

- 云林标准教案（Word）
- 学生讲义（Word）
- 课堂演示文稿（PowerPoint）
- 教师授课计划表（Word，可与学期教案同步生成）
- 课程实验计划表（Word，按班级分别生成）

系统只使用仓库内置的云南林业职业技术学院固定模板。模板是只读资源，不支持上传、删除或在线编辑；每次生成前都会校验 SHA-256、页面方向、表格结构、标题与必需字段。

## 技术栈

- 后端：FastAPI、SQLite、python-docx、docxtpl、python-pptx
- 前端：React、TypeScript、Vite、Ant Design、Electron
- AI：DeepSeek 或 Anthropic

## 快速启动

### 后端

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python run_backend.py
```

后端默认地址为 `http://127.0.0.1:8000`，健康检查为 `GET /health`。

### 前端

```powershell
cd frontend
npm install
npm run dev
```

前端默认地址为 `http://localhost:5173`。

也可以直接使用根目录的 `start.bat`（Windows）或 `./start.sh`（Linux/macOS）。

## 环境变量

从 `.env.example` 或 `backend/.env.example` 复制一份 `.env`，至少配置一个 AI 提供商：

```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-api-key

# 或使用 Anthropic
# AI_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your-api-key
```

## 固定模板与校验

内置模板位于：

```text
backend/resources/templates/yunlin_lesson_plan.docx
backend/resources/templates/yunlin_teaching_plan.docx
backend/resources/templates/yunlin_experiment_plan.docx
```

模板接口均为只读：

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/templates` | GET | 返回唯一的云林模板 |
| `/api/templates/validation` | GET | 获取模板校验结果与 SHA-256 指纹 |
| `/api/templates/validation` | POST | 重新执行校验 |
| `/api/templates/validation/all` | GET | 校验教案、授课计划和实验计划三个固定资源 |
| `/api/templates/yunlin-standard` | GET | 获取模板元数据 |
| `/api/templates/yunlin-standard/download` | GET | 下载内置模板 |

## 统一备课 API

`POST /api/preparation` 接收一次课程信息和一个或多个产物类型：

```json
{
  "subject": "Python程序设计",
  "grade": "大一",
  "topic": "列表的创建与应用",
  "duration": "2课时",
  "artifact_types": ["lesson_plan", "handout", "presentation"],
  "location": "实训室301",
  "generate_reflection": false
}
```

响应会返回生成内容摘要及每个文件的下载地址。支持的产物类型：

- `lesson_plan`：套用固定云林模板的教案
- `handout`：面向学生的课堂讲义
- `presentation`：课堂 PPT

`GET /api/preparation/capabilities` 可查询当前固定模板状态及支持的产物类型。

## 学期教案与计划同步生成

在“批量备课”中可勾选教师授课计划表、课程实验计划表。系统以每两份教案作为一周课表：

- 授课计划按课程生成 1 份，所选班级合并写入同一文档，固定模板最多 16 周。
- 实验计划按“课程 + 班级”分别生成，每个班一份，固定模板最多 18 条实验记录。
- 实验项目全部留空时按每周课题自动生成；填写部分实验项目时，仅填写过的周次进入实验计划。
- 学年、学期和教师由批量备课表单统一提供；制表日期、首课日期、节次和实验室仅在生成实验计划时必填。

所有教案、授课计划和实验计划完成后会打包为同一个 ZIP 文件。

## 项目结构

```text
backend/
  api/                    FastAPI 接口
  services/               AI、模板校验与文件渲染
  resources/templates/    固定云林模板
  models/                 Pydantic 模型与 SQLite
  tests/                  后端测试
frontend/
  src/pages/              React 页面
  src/services/           API 客户端
  electron/               桌面应用封装
storage/                  上传、输出与数据库等运行时数据
```

## 测试与构建

```powershell
# 后端
.\.venv\Scripts\python.exe -m pytest backend\tests

# 前端
cd frontend
npm run build
```

API 文档启动后可在 `http://127.0.0.1:8000/docs` 查看。
