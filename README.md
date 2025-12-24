# 智能教案助手

一款基于 AI 的教案生成与编辑工具，支持模板管理、智能生成和在线编辑功能。

## 功能特性

- **模板管理** - 上传、预览和管理教案模板 (.docx)
- **智能生成** - 基于 AI 自动生成教案内容
- **在线编辑** - 富文本编辑器支持教案内容编辑
- **AI 优化** - 一键优化教案内容
- **文档导出** - 支持导出为 Word 文档格式
- **桌面应用** - 支持 Electron 桌面应用

## 快速开始

### 方式一：Web 应用模式

#### 1. 环境准备

确保已安装：
- Python 3.8+
- Node.js 16+

#### 2. 后端启动

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

# 配置环境变量（创建 .env 文件）
echo AI_PROVIDER=deepseek > .env
echo DEEPSEEK_API_KEY=your_api_key_here >> .env

# 启动后端
python run_backend.py
```

后端将在 `http://127.0.0.1:8000` 启动

#### 3. 前端启动

```bash
# 新开一个终端窗口
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 启动

### 方式二：桌面应用模式

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 构建前端并启动 Electron
npm run electron:dev
```

### 方式三：打包桌面应用

```bash
cd frontend
npm run build
npm run electron:build
```

打包后的安装包位于 `frontend/dist-electron/` 目录

## 环境变量配置

在项目根目录创建 `.env` 文件：

```env
# AI 服务配置
AI_PROVIDER=deepseek              # 可选: deepseek, anthropic
DEEPSEEK_API_KEY=sk-xxx           # DeepSeek API Key
ANTHROPIC_API_KEY=sk-ant-xxx      # Anthropic API Key (可选)

# 服务配置（可选）
API_HOST=0.0.0.0
API_PORT=8000
```

> 获取 API Key：
> - DeepSeek: https://platform.deepseek.com/
> - Anthropic: https://console.anthropic.com/

## 技术栈

### 后端
- **FastAPI** - 高性能异步 Web 框架
- **SQLite** - 轻量级数据库
- **python-docx** - Word 文档处理
- **DocxTemplate** - Word 模板渲染

### 前端
- **React 18** - 用户界面框架
- **TypeScript** - 类型安全
- **Vite** - 快速构建工具
- **Ant Design** - UI 组件库
- **TipTap** - 富文本编辑器
- **Zustand** - 状态管理

### 桌面应用
- **Electron** - 跨平台桌面应用框架

## 项目结构

```
lessonToos/
├── backend/                    # 后端服务
│   ├── api/                   # API 路由
│   │   ├── templates.py       # 模板管理
│   │   ├── generate.py        # 教案生成
│   │   ├── edit.py            # AI 编辑
│   │   ├── documents.py       # 文档管理
│   │   └── settings.py        # 设置管理
│   ├── models/                # 数据模型
│   ├── services/              # 业务逻辑
│   ├── utils/                 # 工具函数
│   ├── config.py              # 配置管理
│   └── main.py                # 应用入口
│
├── frontend/                   # 前端应用
│   ├── electron/              # Electron 主进程
│   └── src/
│       ├── components/        # React 组件
│       ├── pages/             # 页面组件
│       ├── services/          # API 服务
│       └── stores/            # 状态管理
│
├── storage/                    # 存储目录
│   ├── templates/             # 模板文件
│   ├── uploads/               # 上传文件
│   ├── outputs/               # 生成文档
│   └── database.db            # SQLite 数据库
│
├── run_backend.py             # 后端启动脚本
└── .env                       # 环境变量配置
```

## API 文档

启动后端后访问：
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 核心 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/templates` | GET | 获取模板列表 |
| `/api/templates` | POST | 上传新模板 |
| `/api/templates/{id}` | DELETE | 删除模板 |
| `/api/generate` | POST | 生成教案 |
| `/api/edit/optimize` | POST | AI 优化内容 |
| `/api/edit/expand` | POST | AI 扩展内容 |
| `/api/edit/rewrite` | POST | AI 重写内容 |
| `/api/documents/download/{filename}` | GET | 下载文档 |
| `/api/settings` | GET/POST | 管理设置 |

## 使用指南

### 创建模板

1. 在 Word 中创建教案模板
2. 使用 `{{ 变量名 }}` 语法标记可替换内容
3. 上传模板到系统

```
课程名称: {{ course_name }}
授课教师: {{ teacher_name }}
授课时间: {{ teaching_date }}
教学目标: {{ teaching_objectives }}
```

### 生成教案

1. 选择模板
2. 填写生成参数（课程名称、主题等）
3. 点击生成按钮
4. 等待 AI 生成内容

### 编辑导出

1. 在编辑器中查看生成内容
2. 可使用 AI 辅助优化/扩展/重写
3. 手动编辑调整
4. 导出为 Word 文档

## 常见问题

**Q: 后端启动失败？**
- 检查虚拟环境是否激活
- 检查依赖是否正确安装
- 检查 `.env` 文件中的 API Key 是否正确

**Q: AI 生成失败？**
- 确认 API Key 有效且有足够额度
- 检查网络连接
- 查看 API 服务状态

**Q: 前端无法连接后端？**
- 确认后端服务已启动
- 检查端口是否被占用
- 查看浏览器控制台错误信息

## 开发

### 运行测试

```bash
# 后端测试
cd backend
pytest

# API 测试
python test_api.py
```

### 代码规范

- 后端遵循 PEP 8 规范
- 前端使用 ESLint + TypeScript 规范

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
