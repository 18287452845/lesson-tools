# Docker部署指南

本指南详细说明如何使用Docker在本地部署智能教案助手。

## 目录

- [前提条件](#前提条件)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [常用命令](#常用命令)
- [数据持久化](#数据持久化)
- [开发模式](#开发模式)
- [故障排查](#故障排查)
- [性能优化](#性能优化)

---

## 前提条件

确保您的系统已安装以下软件：

1. **Docker** (版本 20.10 或更高)
   - 安装指南: https://docs.docker.com/get-docker/
   - 验证安装: `docker --version`

2. **Docker Compose** (版本 2.0 或更高)
   - 通常随Docker Desktop一起安装
   - 验证安装: `docker-compose --version`

3. **系统要求**
   - 可用内存: 至少 2GB
   - 可用磁盘空间: 至少 5GB
   - 操作系统: Linux、macOS、Windows 10/11

---

## 快速开始

### 1. 克隆或下载项目

```bash
cd /path/to/lesson-tools
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑.env文件，填入您的API密钥
# Linux/Mac:
nano .env
# Windows:
notepad .env
```

**必填配置项**:
```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

### 3. 启动服务

```bash
# 构建并启动所有服务（首次运行）
docker-compose up -d --build

# 后续启动（无需重新构建）
docker-compose up -d
```

### 4. 访问应用

- **前端界面**: http://localhost
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc

### 5. 验证部署

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 检查健康状态
curl http://localhost:8000/health
curl http://localhost
```

---

## 详细配置

### 环境变量说明

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `AI_PROVIDER` | AI提供商 (`deepseek` 或 `anthropic`) | `deepseek` | ✅ |
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | - | ✅ (使用DeepSeek时) |
| `ANTHROPIC_API_KEY` | Anthropic API密钥 | - | ❌ (使用Claude时必填) |
| `DEEPSEEK_BASE_URL` | DeepSeek OpenAI兼容接口地址 | `https://api.deepseek.com` | ❌ |
| `AI_MODEL` | AI模型名称 | `deepseek-v4-flash` | ❌ |
| `AI_MAX_TOKENS` | 最大token数 | `4096` | ❌ |
| `AI_TEMPERATURE` | 生成温度 (0.0-1.0) | `0.7` | ❌ |
| `API_HOST` | API服务主机 | `0.0.0.0` | ❌ |
| `API_PORT` | API服务端口 | `8000` | ❌ |

### 获取API密钥

**DeepSeek**:
1. 访问 https://platform.deepseek.com/
2. 注册并登录账户
3. 在控制台创建API密钥

**Anthropic Claude** (可选):
1. 访问 https://console.anthropic.com/
2. 注册并登录账户
3. 在设置中创建API密钥

### 端口配置

如果默认端口（80和8000）已被占用，可以修改`docker-compose.yml`中的端口映射：

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # 主机端口:容器端口

  frontend:
    ports:
      - "8080:80"    # 主机端口:容器端口
```

修改后访问地址:
- 前端: http://localhost:8080
- 后端: http://localhost:8001

---

## 常用命令

### 服务管理

```bash
# 启动服务（后台运行）
docker-compose up -d

# 启动服务（前台运行，查看实时日志）
docker-compose up

# 停止服务
docker-compose stop

# 停止并删除容器（保留数据卷）
docker-compose down

# 停止并删除容器、网络、卷（完全清理）
docker-compose down -v

# 重启服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
docker-compose restart frontend
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 实时跟踪日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend

# 查看最近100行日志
docker-compose logs --tail=100
```

### 容器管理

```bash
# 查看运行中的容器
docker-compose ps

# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 在后端容器中执行命令
docker-compose exec backend python -m pytest

# 查看容器资源使用情况
docker stats
```

### 镜像管理

```bash
# 重新构建镜像
docker-compose build

# 强制重新构建（不使用缓存）
docker-compose build --no-cache

# 重新构建特定服务
docker-compose build backend

# 拉取最新镜像
docker-compose pull

# 清理未使用的镜像
docker image prune -a
```

---

## 数据持久化

### 存储目录结构

应用数据存储在`storage`目录中，该目录会被挂载到容器内：

```
storage/
├── templates/      # 用户上传的.docx模板
├── uploads/        # 临时上传文件
├── outputs/        # 生成的.docx文档
├── exports/        # 批量导出的ZIP文件
└── database.db     # SQLite数据库
```

### 备份数据

```bash
# 备份整个storage目录
tar -czf backup-$(date +%Y%m%d).tar.gz storage/

# 仅备份数据库
cp storage/database.db storage/database.db.backup

# 恢复备份
tar -xzf backup-20260106.tar.gz
```

### 迁移数据

停止服务后，将`storage`目录复制到新环境即可：

```bash
# 停止服务
docker-compose down

# 复制数据到新服务器
rsync -avz storage/ user@new-server:/path/to/lesson-tools/storage/

# 在新服务器上启动服务
docker-compose up -d
```

---

## 开发模式

### 启用代码热重载

在`docker-compose.yml`中取消以下注释，将本地代码挂载到容器：

```yaml
backend:
  volumes:
    - ./storage:/app/storage
    - ./backend:/app/backend  # 取消此行注释
```

修改后重启服务：
```bash
docker-compose down
docker-compose up -d
```

### 前端开发模式

对于前端开发，建议直接在本地运行Vite开发服务器：

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173，自动连接到Docker运行的后端API。

### 调试技巧

```bash
# 查看后端Python错误
docker-compose logs -f backend | grep -i error

# 进入容器查看文件
docker-compose exec backend ls -la /app/storage

# 在容器内执行Python脚本
docker-compose exec backend python debug_script.py

# 查看数据库内容
docker-compose exec backend python -c "
import sqlite3
conn = sqlite3.connect('storage/database.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM templates')
print(cursor.fetchall())
"
```

---

## 故障排查

### 常见问题

#### 1. 容器启动失败

**症状**: `docker-compose up` 报错或容器立即退出

**解决方法**:
```bash
# 查看详细错误信息
docker-compose logs backend
docker-compose logs frontend

# 检查端口占用
# Linux/Mac:
netstat -tuln | grep -E '80|8000'
# Windows:
netstat -ano | findstr "80 8000"

# 检查.env文件是否存在且配置正确
cat .env
```

#### 2. API密钥错误

**症状**: 后端日志显示 "API key not found" 或 401错误

**解决方法**:
```bash
# 检查.env文件中的API密钥
grep API_KEY .env

# 确保密钥前后无空格
# 错误: DEEPSEEK_API_KEY= sk-xxx (有空格)
# 正确: DEEPSEEK_API_KEY=sk-xxx

# 重启服务使配置生效
docker-compose restart backend
```

#### 3. 数据库锁定错误

**症状**: SQLite database is locked

**解决方法**:
```bash
# 停止所有服务
docker-compose down

# 检查数据库文件权限
ls -l storage/database.db

# 删除锁文件（如果存在）
rm -f storage/database.db-shm storage/database.db-wal

# 重启服务
docker-compose up -d
```

#### 4. 前端无法访问后端

**症状**: 前端显示网络错误或API连接失败

**解决方法**:
```bash
# 检查nginx配置
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# 检查后端健康状态
curl http://localhost:8000/health

# 查看网络连接
docker-compose exec frontend ping backend

# 重启前端服务
docker-compose restart frontend
```

#### 5. 磁盘空间不足

**症状**: No space left on device

**解决方法**:
```bash
# 清理Docker缓存
docker system prune -a --volumes

# 清理未使用的镜像
docker image prune -a

# 检查磁盘使用情况
df -h
du -sh storage/*
```

### 健康检查

```bash
# 检查容器健康状态
docker-compose ps

# 手动触发健康检查
docker inspect --format='{{json .State.Health}}' lesson-tools-backend | python -m json.tool
docker inspect --format='{{json .State.Health}}' lesson-tools-frontend | python -m json.tool

# 测试API端点
curl -I http://localhost:8000/health
curl -I http://localhost/
```

---

## 性能优化

### 资源限制

在`docker-compose.yml`中添加资源限制：

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G

frontend:
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 512M
```

### 日志轮转

限制日志文件大小：

```yaml
backend:
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

### 生产环境优化

```bash
# 使用生产配置启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 禁用代码挂载
# 在docker-compose.yml中注释掉 - ./backend:/app/backend

# 使用Alpine镜像减小体积
# 已在Dockerfile中使用python:3.11-slim和nginx:alpine
```

---

## 安全建议

1. **保护API密钥**
   - 不要将`.env`文件提交到Git仓库
   - 使用强密码和定期更换API密钥

2. **网络隔离**
   - 生产环境中考虑使用反向代理（nginx/traefik）
   - 配置防火墙限制访问

3. **数据加密**
   - 定期备份数据库
   - 考虑对敏感数据进行加密存储

4. **更新维护**
   - 定期更新Docker镜像
   - 关注安全漏洞公告

---

## 更多信息

- **项目文档**: 查看项目根目录的 `README.md` 和 `CLAUDE.md`
- **API文档**: http://localhost:8000/docs
- **问题反馈**: 提交Issue到项目仓库

---

## 卸载

完全删除应用和所有数据：

```bash
# 停止并删除容器、网络、卷
docker-compose down -v

# 删除镜像
docker rmi lesson-tools-backend lesson-tools-frontend

# 清理storage目录（可选）
rm -rf storage/

# 删除.env文件（可选）
rm .env
```

---

**最后更新**: 2026-01-06
