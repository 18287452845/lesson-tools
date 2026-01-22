# 智能教案助手 (Intelligent Lesson Plan Assistant)

<div align="center">

一款基于 AI 的教案生成与编辑工具，支持模板管理、智能生成、批量生产和在线编辑功能。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/Node-16+-green.svg)](https://nodejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/18287452845/lesson-tools)

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用指南](#-使用指南) • [API文档](#-api-文档) • [常见问题](#-常见问题)

</div>

---

## 📸 功能预览

| 模板管理 | 批量生成 | 可视化编辑 |
|:---:|:---:|:---:|
| 上传和管理 Word 模板 | 一键生成整学期教案 | TipTap 富文本编辑器 |

## 简介

智能教案助手是一款专为教育工作者设计的全栈 Web 应用，通过人工智能技术大幅简化教案创建流程。无论是单份教案还是整学期批量生成，都能在几分钟内完成专业质量的教案文档。

**核心优势：**
- 🚀 **高效** - 批量生成整学期教案，节省 90% 时间
- 🎨 **专业** - 完美保留 Word 格式，符合学校规范
- 🔄 **灵活** - 可视化模板编辑，自定义教案结构
- 💾 **智能** - AI 优化内容，自动扩展重写

## ✨ 功能特性

### 核心功能
- **📝 模板管理** - 上传、预览和管理教案模板 (.docx)
- **🤖 智能生成** - 基于 AI 自动生成教案内容
- **📦 批量生成** - 按课时数批量生成整学期教案，支持章节缓存
- **✏️ 在线编辑** - 富文本编辑器支持模板内容在线编辑
- **🎨 可视化编辑** - TipTap 富文本编辑器，支持表格、颜色、字体等
- **🔄 版本管理** - 自动保存编辑历史，支持版本对比和回滚
- **👁️ 实时预览** - 预览 Jinja2 模板渲染效果
- **💾 AI 优化** - 一键优化、扩展、重写教案内容
- **📄 文档导出** - 支持导出为 Word 文档格式（完美保留格式和表格）
- **🔌 多 AI 提供商** - 支持 DeepSeek 和 Anthropic Claude
- **💻 桌面应用** - 支持 Electron 跨平台桌面应用
- **📚 教材章节层级** - 默认支持教材-章节-小节三层结构

### 模板编辑器特性
- **Jinja2 语法支持** - 可视化插入变量、循环和条件
- **格式工具栏** - 加粗、斜体、下划线、颜色、字体等
- **表格编辑** - 完整的表格操作（插入、删除、合并单元格）
- **自动保存** - 3秒防抖自动保存，避免数据丢失
- **语法验证** - 实时验证 Jinja2 语法错误
- **DOCX ↔ HTML** - 双向无损转换，保留原始格式

### 批量生成特性
- **课时数驱动** - 输入总课时（如64、72），自动计算教案数量
- **灵活分组** - 可配置每份教案课时数（默认2课时/教案）
- **章节缓存** - 生成的章节模板自动缓存，支持快速复用
- **多种输入方式** - AI自动生成章节或手动输入章节标题
- **实时进度** - 后台生成，实时查看进度和状态
- **ZIP打包** - 所有教案自动打包下载，文件命名清晰

## 📋 系统要求

- **Python**: 3.8+ (推荐 3.10+，已测试 3.12.3)
- **Node.js**: 16+ (推荐 18+)
- **操作系统**: Windows / macOS / Linux
- **磁盘空间**: 至少 500MB 可用空间
- **内存**: 建议 4GB+

## 🚀 快速开始

### 方式一：Web 应用模式

#### 1. 克隆项目

```bash
git clone https://github.com/18287452845/lesson-tools.git
cd lesson-tools
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp backend/.env.example .env

# 编辑 .env 文件，填入你的 API Key
# Windows 用户可使用: notepad .env
# Linux/Mac 用户可使用: nano .env 或 vim .env
```

**.env 文件示例：**
```env
# 必填：选择AI提供商
AI_PROVIDER=deepseek

# 必填：DeepSeek API Key（从 https://platform.deepseek.com/ 获取）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：Anthropic API Key（从 https://console.anthropic.com/ 获取）
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：服务器配置
# API_HOST=127.0.0.1
# API_PORT=8000
```

#### 3. 后端启动

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r backend/requirements.txt

# 启动后端服务
python run_backend.py
```

后端将在 `http://127.0.0.1:8000` 启动

**验证后端是否成功启动：**
- 访问 http://127.0.0.1:8000/health 应返回 `{"status": "healthy"}`
- 访问 http://127.0.0.1:8000/docs 查看 API 文档

#### 4. 前端启动

```bash
# 新开一个终端窗口
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 启动

### 管理脚本（便捷启动/停止）

项目提供了跨平台的管理脚本来简化启动和停止操作：

**Windows:**
```batch
# 启动前后端服务
start.bat

# 查看服务状态
status.bat

# 停止服务
stop.bat
```

**Linux/Mac:**
```bash
# 启动前后端服务
./start.sh

# 查看服务状态
./status.sh

# 停止服务
./stop.sh
```

**脚本功能：**
- `start.bat/sh` - 后台启动前后端服务，日志保存在 `logs/` 目录
- `status.bat/sh` - 查看服务运行状态和端口监听情况
- `stop.bat/sh` - 停止所有服务并清理遗留进程

### 方式二：桌面应用模式

桌面应用模式仍需要后端服务运行。

```bash
# 1. 先按照方式一启动后端服务
python run_backend.py

# 2. 新开终端，进入前端目录
cd frontend

# 3. 安装依赖
npm install

# 4. 启动 Electron 开发模式
npm run electron:dev
```

### 方式三：打包桌面应用

```bash
# 1. 进入前端目录
cd frontend

# 2. 构建前端资源
npm run build

# 3. 打包 Electron 应用
npm run electron:build
```

打包后的安装包位于 `frontend/dist-electron/` 目录

**注意：** 桌面应用仍需要后端服务支持，建议将后端一起打包或提供独立的后端安装包。

### 方式四：Docker 部署（推荐用于生产环境）

使用 Docker Compose 可以快速部署整个应用，无需手动配置 Python 和 Node.js 环境。

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入您的 API Key

# 2. 构建并启动服务
docker-compose up -d --build

# 3. 查看运行状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f

# 5. 停止服务
docker-compose down
```

**访问地址：**
- 前端界面：http://localhost:8081
- 后端 API：http://localhost:8001
- API 文档：http://localhost:8001/docs

**数据持久化：** `storage/` 目录中的数据会自动挂载并持久化保存。

详细的 Docker 部署说明请参考 `DOCKER_DEPLOYMENT.md`。

## 🎯 AI 提供商配置

本项目支持两种 AI 提供商，可根据需求选择：

### DeepSeek（推荐）

- **优势**: 性价比高，中文理解优秀，API 稳定
- **价格**: 相对便宜
- **获取 API Key**: https://platform.deepseek.com/
- **默认模型**: `deepseek-chat`

```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-key
```

### Anthropic Claude

- **优势**: 高质量输出，强大的推理能力
- **价格**: 相对较贵
- **获取 API Key**: https://console.anthropic.com/
- **默认模型**: `claude-sonnet-4-20250514`

```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

### 运行时切换 AI 提供商

也可以在应用的**设置页面**动态切换 AI 提供商，无需重启服务。

## 🛠 技术栈

### 后端
- **FastAPI** 0.109+ - 高性能异步 Web 框架
- **Uvicorn** - ASGI 服务器
- **SQLite + aiosqlite** - 异步轻量级数据库
- **python-docx** 1.1+ - Word 文档处理
- **docxtpl** 0.16+ - Word 模板渲染（Jinja2）
- **mammoth** 1.6+ - .docx → HTML 转换
- **htmldocx** 0.0.6+ - HTML → .docx 转换
- **beautifulsoup4** - HTML 解析
- **Anthropic SDK** 0.18+ - Anthropic API 客户端
- **httpx** - 异步 HTTP 客户端（DeepSeek API）
- **Pydantic** 2.5+ - 数据验证和设置管理

### 前端
- **React** 18.2 - 用户界面框架
- **TypeScript** 5.3 - 类型安全
- **Vite** 5.0 - 快速构建工具
- **Ant Design** 5.13 - UI 组件库
- **TipTap** 2.1 - 富文本编辑器
  - Table、Color、TextStyle、FontFamily 等多个扩展
- **Zustand** 4.4 - 轻量级状态管理
- **Axios** - HTTP 客户端
- **React Router** 6.21 - 路由管理
- **Nunjucks** 3.2 - Jinja2 模板预览

### 桌面应用
- **Electron** 28+ - 跨平台桌面应用框架
- **electron-builder** - 应用打包工具

## 📁 项目结构

```
lesson-tools/
├── backend/                    # 后端服务
│   ├── api/                   # API 路由层
│   │   ├── templates.py       # 模板管理 API (18个端点)
│   │   ├── generate.py        # AI 教案生成 API
│   │   ├── lesson_plans.py    # 教案检索管理 API
│   │   ├── edit.py            # AI 编辑 API
│   │   ├── documents.py       # 文档管理 API
│   │   ├── settings.py        # 设置管理 API
│   │   ├── batch.py           # 批量生成 API 📦
│   │   └── classes.py         # 班级管理 API
│   ├── models/                # 数据模型
│   │   ├── database.py        # 数据库连接和表定义
│   │   └── schemas.py         # Pydantic 数据模型
│   ├── services/              # 业务逻辑层
│   │   ├── ai_provider.py     # AI 提供商抽象（工厂模式）
│   │   ├── ai_generator.py    # 教案生成服务
│   │   ├── ai_editor.py       # AI 编辑服务
│   │   ├── template_parser.py # 模板解析（Jinja2）
│   │   ├── template_sync.py   # 模板自动同步服务
│   │   ├── template_versioning.py # 版本历史管理
│   │   ├── document_renderer.py # 文档渲染（docxtpl）
│   │   ├── document_modifier.py # 文档修改服务
│   │   ├── lesson_plan_service.py # 教案业务逻辑
│   │   ├── docx_converter.py  # DOCX ↔ HTML 双向转换
│   │   ├── jinja_protector.py # Jinja2 语法保护
│   │   ├── chapter_splitter.py # 课程章节拆分服务 📦
│   │   ├── batch_processor.py # 批量生成处理器 📦
│   │   └── background_runner.py # 后台任务运行器 📦
│   ├── tests/                 # 后端测试
│   │   ├── conftest.py        # Pytest 配置和 Fixtures
│   │   ├── test_api_templates.py # 模板 API 测试
│   │   ├── test_api_batch.py # 批量 API 测试
│   │   ├── test_database.py # 数据库测试
│   │   └── ...                # 其他测试文件
│   ├── config.py              # 配置管理（Pydantic Settings）
│   ├── main.py                # FastAPI 应用入口
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # 前端应用
│   ├── electron/              # Electron 主进程
│   │   ├── main.js            # Electron 入口
│   │   └── preload.js         # 预加载脚本
│   └── src/
│       ├── components/        # React 组件
│       │   └── Editor/        # 富文本编辑器组件 (10个)
│       │       ├── TipTapEditor.tsx      # 主编辑器
│       │       ├── EditorToolbar.tsx     # 工具栏
│       │       ├── TableToolbar.tsx      # 表格工具栏
│       │       ├── JinjaInsertModal.tsx  # Jinja2 插入弹窗
│       │       ├── PreviewPanel.tsx      # 预览面板
│       │       ├── VersionHistory.tsx    # 版本历史
│       │       └── ...                   # 其他扩展
│       ├── pages/             # 页面组件
│       │   ├── Home.tsx       # 首页
│       │   ├── TemplateManager.tsx # 模板管理
│       │   ├── TemplateEditor.tsx  # 模板编辑器 ⭐
│       │   ├── NewLessonPlan.tsx   # 新建教案
│       │   ├── EditLessonPlan.tsx  # 编辑教案
│       │   ├── LessonPlanDetail.tsx # 教案详情
│       │   ├── History.tsx    # 历史记录
│       │   ├── BatchGenerate.tsx  # 批量生成 📦
│       │   ├── BatchDownloads.tsx # 批量下载 📦
│       │   ├── BatchTaskDetail.tsx # 批量任务详情 📦
│       │   ├── CachedLessonPlans.tsx # 缓存章节模板 📦
│       │   ├── ClassManager.tsx # 班级管理
│       │   └── Settings.tsx   # 设置
│       ├── services/          # API 服务
│       │   ├── api.ts         # 主 API 客户端
│       │   ├── batchApi.ts    # 批量生成 API 客户端 📦
│       │   ├── settingsApi.ts # 设置 API
│       │   └── fileService.ts # 文件下载服务
│       ├── stores/            # Zustand 状态管理
│       │   ├── templateStore.ts       # 模板状态
│       │   ├── templateEditorStore.ts # 编辑器状态 ⭐
│       │   ├── generatorStore.ts      # 生成器状态
│       │   ├── editorStore.ts         # 编辑器状态
│       │   └── settingsStore.ts       # 设置状态
│       ├── hooks/             # React Hooks
│       │   └── useAutoSave.ts # 自动保存 Hook ⭐
│       └── types/             # TypeScript 类型定义
│
├── storage/                    # 存储目录（自动创建）
│   ├── templates/             # 用户上传的模板文件
│   ├── uploads/               # 临时上传文件
│   ├── outputs/               # 生成的 Word 文档
│   └── database.db            # SQLite 数据库
│
├── test-data/                  # 测试数据
│   └── mock-responses.json    # Mock AI 响应
│
├── test-results/              # 测试结果输出
│   └── screenshots/          # E2E 测试截图
│
├── logs/                      # 服务日志（自动创建）
│
├── run_backend.py             # 后端启动脚本
├── verify_backend.py          # 后端环境验证脚本
├── pytest.ini                 # Pytest 配置
├── start.bat / start.sh       # 启动前后端服务（Windows/Linux）
├── status.bat / status.sh     # 查看服务状态
├── stop.bat / stop.sh         # 停止服务
├── .env                       # 环境变量配置（需创建）
├── .gitignore                 # Git 忽略规则
├── CLAUDE.md                  # Claude Code 项目说明
├── WORD_EXPORT_FIX.md         # Word 导出技术说明
├── REALTIME_GENERATION_FEATURE.md # 实时生成功能说明
└── README.md                  # 本文件
```

## 📡 API 文档

启动后端后访问：
- **Swagger UI**: `http://127.0.0.1:8000/docs` - 交互式 API 文档
- **ReDoc**: `http://127.0.0.1:8000/redoc` - 美观的 API 文档
- **Health Check**: `http://127.0.0.1:8000/health` - 健康检查

### 核心 API 端点

#### 模板管理
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/templates` | GET | 获取模板列表 |
| `/api/templates/upload` | POST | 上传新模板 |
| `/api/templates/{id}` | GET | 获取模板详情 |
| `/api/templates/{id}` | PATCH | 更新模板元数据 |
| `/api/templates/{id}` | DELETE | 删除模板 |
| `/api/templates/{id}/download` | GET | 下载模板 |

#### 模板编辑器 API ⭐
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/templates/{id}/html` | GET | 获取 HTML 编辑格式 |
| `/api/templates/{id}/save-html` | POST | 保存 HTML 为 .docx |
| `/api/templates/{id}/preview-html` | POST | 预览渲染效果 |
| `/api/templates/{id}/validate-jinja` | POST | 验证 Jinja2 语法 |

#### 版本历史 API ⭐
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/templates/{id}/versions` | GET | 获取版本列表 |
| `/api/templates/{id}/versions/{vid}` | GET | 获取版本内容 |
| `/api/templates/{id}/versions/compare` | POST | 对比两个版本 |
| `/api/templates/{id}/versions/{vid}/restore` | POST | 恢复版本 |
| `/api/templates/{id}/versions/cleanup` | DELETE | 清理旧版本 |

#### 教案生成
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/generate` | POST | 生成教案 |
| `/api/generate/stream` | POST | SSE 流式生成 |
| `/api/generate/{id}/regenerate-field` | POST | 重新生成单个字段 |
| `/api/generate/{id}/export` | POST | 导出为 Word 文档 |
| `/api/generate` | GET | 获取教案列表 |
| `/api/generate/{id}` | GET | 获取教案详情 |
| `/api/generate/{id}` | DELETE | 删除教案 |

#### AI 编辑
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/edit/upload` | POST | 上传现有文档 |
| `/api/edit/{id}` | GET | 获取文档详情 |
| `/api/edit/{id}/section` | POST | 编辑特定章节 |
| `/api/edit/{id}/ai-enhance` | POST | AI 增强内容 |
| `/api/edit/{id}/add-section` | POST | 添加缺失章节 |
| `/api/edit/{id}/save` | POST | 保存并下载 |
| `/api/edit/{id}/undo` | POST | 撤销编辑 |
| `/api/edit/{id}/history` | GET | 获取编辑历史 |

#### 设置管理
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/settings/ai-provider` | GET/POST | 获取/设置 AI 提供商 |
| `/api/settings/ai-providers` | GET | 获取可用 AI 提供商列表 |
| `/api/settings/app-info` | GET | 获取应用信息 |

#### 批量生成 📦
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/batch/split-chapters` | POST | 根据总课时拆分章节 |
| `/api/batch/split-chapters-stream` | POST | SSE 流式章节拆分 |
| `/api/batch/create-task` | POST | 创建批量生成任务 |
| `/api/batch/tasks/{id}` | GET | 获取任务状态和进度 |
| `/api/batch/tasks` | GET | 获取批量任务列表 |
| `/api/batch/tasks/{id}/download` | GET | 下载生成的 ZIP 文件 |
| `/api/batch/tasks/{id}` | DELETE | 取消或删除任务 |
| `/api/batch/chapter-templates` | GET | 获取缓存的章节模板列表 |

#### 班级管理
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/classes` | GET/POST | 获取/创建班级 |
| `/api/classes/{id}` | GET | 获取班级详情 |
| `/api/classes/{id}` | PUT | 更新班级 |
| `/api/classes/{id}` | DELETE | 删除班级 |

## 📖 使用指南

### 1. 上传模板

在 Word 中创建教案模板，使用 Jinja2 语法标记可替换内容：

**基本变量：**
```
课程名称: {{ subject }}
年级: {{ grade }}
课题: {{ topic }}
课时: {{ duration }}
授课教师: {{ teacher_name }}
```

**多行内容：**
```
教学目标：
{{ teaching_goals }}

教学重点：
{{ key_points }}
```

**循环（教学步骤）：**
```
{% for step in teaching_steps %}
{{ loop.index }}. {{ step.title }}
   时间：{{ step.duration }}
   内容：{{ step.content }}
{% endfor %}
```

**条件判断：**
```
{% if homework %}
作业布置：
{{ homework }}
{% endif %}
```

**嵌套结构（教学目标分类）：**
```
{% for goal_type in ['知识目标', '能力目标', '素质目标'] %}
{{ goal_type }}：
{% for goal in teaching_goals[goal_type] %}
- {{ goal }}
{% endfor %}

{% endfor %}
```

### 2. 在线编辑模板 ⭐

1. 进入**模板管理**页面
2. 点击模板右侧的**编辑**按钮
3. 进入可视化模板编辑器：
   - 使用富文本工具栏编辑内容
   - 点击**插入 Jinja2** 按钮添加变量、循环或条件
   - 支持表格编辑、颜色、字体等格式
   - 自动保存（3秒防抖）
   - 查看版本历史并随时回滚

### 3. 生成教案

1. 进入**新建教案**页面
2. 选择模板
3. 填写基本信息（学科、年级、课题等）
4. 点击**生成**按钮
5. AI 会根据模板结构生成完整教案内容
6. 可对单个字段进行重新生成
7. 导出为 Word 文档

### 4. AI 编辑功能

在编辑器中选中文本后，可使用以下 AI 功能：
- **优化**: 改进语言表达，使内容更流畅专业
- **扩展**: 在现有内容基础上增加细节和深度
- **重写**: 用不同方式重新表达相同内容

### 5. 导出 Word 文档

1. 编辑完成后，点击**导出文档**按钮
2. 系统使用 `docxtpl` 渲染模板
3. 保留原始格式、表格结构和样式
4. 文档保存在 `storage/outputs/` 目录
5. 可直接下载使用

### 6. 批量生成教案 📦

批量生成功能可以一次性创建整学期的所有教案：

#### 步骤 1: 填写课程信息
- **课程名称**: 如 "Java程序设计"
- **学科/年级**: 选择对应的学科和年级
- **总课时数**: 如 64 课时（自动计算教案数量）
- **每份教案课时**: 默认 2 课时（可调整）
- **章节来源**:
  - **AI 自动生成**: AI 根据课程信息自动拆分章节
  - **手动输入**: 每行输入一个章节标题
  - **使用已有模板**: 复用历史章节配置

#### 步骤 2: 确认章节
- 查看 AI 生成的章节列表
- 可直接在表格中编辑课题和内容概述
- 确认教案模板是否已选择

#### 步骤 3: 监控生成进度
- 后台自动生成所有教案
- 实时显示进度条（已完成/总数）
- 完成后可前往下载页面获取 ZIP 文件

#### 使用已有模板
如果之前生成过相同课程，可选择"使用已有模板"：
- 自动加载历史章节配置
- 一键复用，节省时间
- 模板使用次数会自动记录

#### 下载说明
- 所有教案打包为 ZIP 文件
- 文件命名: `课程名称_批量教案_时间戳.zip`
- 内部文档: `课程名称_01.docx`, `课程名称_02.docx` ...
- 每个文档包含配置数量的教案

### 7. 班级管理

1. 进入**班级管理**页面
2. 点击**添加新班级**
3. 填写班级信息（名称、学科、年级、学生人数等）
4. 保存后可在生成教案时选择班级
5. 支持编辑和删除班级

## ❓ 常见问题

### OnlyOffice 集成

**Q: 打开模板编辑器提示“OnlyOffice Document Server URL not configured”？**

A: 确认后端环境变量已设置且进程重启：
```env
ONLYOFFICE_DOCS_URL=https://your-onlyoffice-domain   # 例如 https://only.linnera.link
ONLYOFFICE_JWT_SECRET=your-jwt-secret                # 文档安全令牌
PUBLIC_BASE_URL=https://your-frontend-domain         # 例如 https://ls.linnera.link
```
Docker 模式修改 `.env` 后需 `docker-compose up -d --build` 重新构建。

**Q: OnlyOffice 提示“文档安全令牌格式不正确”或 JWT 校验失败？**

A: 文档服务器与后端的密钥必须一致，且 Document Server 开启了 JWT 验证。
1. 确认 `.env` 的 `ONLYOFFICE_JWT_SECRET` 与 Document Server `/etc/onlyoffice/documentserver/local.json` 中的 `services.CoAuthoring.secret` 相同。
2. 重启 Document Server（或其容器）和后端。
3. 浏览器清除缓存后重试。

**Q: 控制台报 `inspector.js ... responseType 'arraybuffer'`？**

A: 升级到最新代码并确保 Document Server 使用新的静态版本号（当前为 `20260121-fix8`）。后端会在加载脚本时追加该版本号，Document Server Nginx 需将 `$cache_tag` 设为相同值并为 `inspector.js` 提供占位文件以避免调试脚本拦截。更新后重新部署 Docker 后端与前端。

### 安装和启动

**Q: 后端启动失败，提示"No module named 'fastapi'"？**

A: 虚拟环境未激活或依赖未安装：
```bash
# 确保激活虚拟环境
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r backend/requirements.txt
```

**Q: 前端启动失败，提示"Cannot find module"？**

A: Node 依赖未安装：
```bash
cd frontend
rm -rf node_modules package-lock.json  # 清理
npm install  # 重新安装
```

**Q: 端口被占用怎么办？**

A: 修改端口配置：
```env
# .env 文件
API_PORT=8001  # 修改后端端口
```

### AI 相关

**Q: AI 生成失败，提示"未设置API密钥"？**

A: 检查 `.env` 文件是否正确配置了 API Key。

**Q: DeepSeek API 调用失败？**

A: 可能原因：
1. API Key 无效或过期
2. 账户余额不足
3. 网络问题
4. 请求超时（当前超时设置为 120 秒）

### 模板和编辑

**Q: 上传模板失败，提示"Template validation failed"？**

A: 模板语法错误，检查：
1. 所有 `{{` 都有对应的 `}}`
2. 所有 `{% for %}` 都有对应的 `{% endfor %}`
3. 所有 `{% if %}` 都有对应的 `{% endif %}`

**Q: 为什么 storage/templates/ 中的模板不显示？**

A: 后端会在启动时自动扫描 `storage/templates/` 文件夹并导入新模板：
- 只需将 `.docx` 文件放入该文件夹
- 重启后端服务即可自动导入
- 已导入的模板不会重复导入

**Q: 如何手动导入现有模板？**

A: 运行导入脚本：
```bash
python import_templates.py
```
这会扫描 `storage/templates/` 文件夹并导入所有未在数据库中的模板。

**Q: Word 导出后格式丢失？**

A: 项目已修复此问题（使用 `docxtpl` 库），确保：
- `backend/services/document_renderer.py` 使用 `DocxTemplate`
- 如果问题依然存在，运行测试：`python test_docxtpl.py`

**Q: 模板编辑器中 Jinja2 语法不显示？**

A: 确保 Jinja2 语法使用正确格式：
- 变量: `{{ variable_name }}`
- 循环: `{% for item in items %}...{% endfor %}`
- 条件: `{% if condition %}...{% endif %}`

### 批量生成相关

**Q: 批量生成需要多长时间？**

A: 取决于教案数量和 AI 响应速度：
- 单份教案约 10-30 秒
- 32 份教案约 5-15 分钟
- 建议使用章节缓存功能加速

**Q: 批量生成失败怎么办？**

A: 系统会记录失败数量，已生成的教案不会丢失：
- 查看错误信息了解原因
- 检查 API 密钥是否有效
- 可以重新创建任务

**Q: 如何修改已缓存的章节模板？**

A: 目前不支持直接修改，可以：
- 创建新任务时手动调整章节
- 或联系管理员删除缓存后重新生成

## 🧪 开发

### 运行测试

```bash
# 后端单元测试
cd backend
pytest

# 运行特定类别的测试
pytest -m unit              # 仅运行单元测试（快速）
pytest -m integration       # 仅运行集成测试
pytest -m api               # 仅运行 API 测试
pytest -m service           # 仅运行服务层测试
pytest -m "not slow"        # 跳过慢速测试
pytest -m "not ai"          # 跳过需要 AI API 密钥的测试
pytest -m smoke             # 快速冒烟测试

# 带覆盖率报告的测试
pytest --cov=backend --cov-report=html

# API 集成测试
python test_api.py

# 模板解析测试
python debug_template.py

# 文档渲染测试
python test_renderer.py
python test_docxtpl.py

# 环境验证
python verify_backend.py
```

### 代码规范

**后端（Python）：**
- 遵循 PEP 8 规范
- 使用类型注解（Type Hints）
- 文档字符串使用 Google 风格
- 异步函数使用 `async/await`

**前端（TypeScript）：**
- 使用 TypeScript 严格模式
- 组件使用函数式组件 + Hooks
- 遵循 React 最佳实践
- CSS 使用 Ant Design 主题系统

### 测试标记

项目使用 pytest 标记来分类测试：
- `unit` - 单元测试（快速、隔离）
- `integration` - 集成测试（较慢、可能使用外部服务）
- `slow` - 慢速测试（数据库、文件 I/O、AI 调用）
- `api` - API 端点测试
- `service` - 服务层测试
- `database` - 数据库操作测试
- `ai` - 调用 AI 提供商的测试（需要 API 密钥）
- `smoke` - 快速冒烟测试

## 🔐 安全最佳实践

⚠️ **重要安全提示**：

1. **保护 API Key**
   - 永远不要将 `.env` 文件提交到 Git
   - 不要在代码中硬编码 API Key
   - 定期轮换 API Key

2. **生产环境部署**
   - 修改 CORS 配置，限制允许的域名
   - 使用 HTTPS 保护 API 通信
   - 添加速率限制防止滥用
   - 设置防火墙规则

3. **数据安全**
   - 定期备份数据库
   - 限制 `storage/` 目录的访问权限
   - 不要在模板中包含敏感信息

## 📄 许可证

MIT License

## 📝 更新日志

### v1.0.0 (最新)
- ✨ 新增批量生成功能 - 按课时数批量生成整学期教案
- ✨ 新增章节缓存系统 - 支持快速复用历史章节配置
- ✨ 新增可视化模板编辑器 - TipTap 富文本编辑器
- ✨ 新增版本历史管理 - 支持版本对比和回滚
- ✨ 新增班级管理功能 - 管理授课班级信息
- ✨ 新增 Docker 部署支持 - 一键部署完整应用栈
- 🔧 优化 Word 导出 - 使用 `docxtpl` 完美保留格式
- 🔧 添加跨平台管理脚本 - Windows .bat 和 Linux .sh
- 🔧 多 AI 提供商支持 - DeepSeek 和 Anthropic Claude
- 🔧 后台任务处理 - 支持优雅关闭和进度追踪
- 🧪 完善测试基础设施 - Pytest 配置和测试标记

---

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 贡献指南

- 提交前运行测试确保通过
- 遵循现有代码风格
- 更新相关文档
- 一个 PR 只做一件事
- 编写清晰的提交信息

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [React](https://react.dev/) - 用户界面库
- [Ant Design](https://ant.design/) - 企业级 UI 组件库
- [TipTap](https://tiptap.dev/) - 无头富文本编辑器
- [docxtpl](https://github.com/elapouya/python-docx-template) - Word 模板引擎
- [DeepSeek](https://www.deepseek.com/) - 高性价比 AI 服务
- [Anthropic](https://www.anthropic.com/) - Claude AI 服务

---

<div align="center">

**开始使用智能教案助手，让 AI 助力教学！** 🎓✨

[⬆ 返回顶部](#智能教案助手-intelligent-lesson-plan-assistant)

</div>
