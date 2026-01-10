# Docker部署 - 快速参考

## 当前部署信息

### 服务访问地址
- **前端界面**: http://localhost:8081
- **后端API**: http://localhost:8001
- **API文档**: http://localhost:8001/docs
- **ReDoc文档**: http://localhost:8001/redoc

### 容器状态
```bash
docker compose ps
```

### 常用命令

#### 服务管理
```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose stop

# 重启服务
docker compose restart

# 停止并删除容器（保留数据）
docker compose down

# 完全清理（包括数据卷）
docker compose down -v
```

#### 日志查看
```bash
# 查看所有日志
docker compose logs

# 实时跟踪日志
docker compose logs -f

# 查看后端日志
docker compose logs backend

# 查看前端日志
docker compose logs frontend
```

#### 进入容器
```bash
# 进入后端容器
docker compose exec backend bash

# 进入前端容器
docker compose exec frontend sh
```

#### 重新构建
```bash
# 重新构建并启动
docker compose up -d --build

# 仅重新构建后端
docker compose build backend

# 仅重新构建前端
docker compose build frontend
```

### 数据持久化

数据存储在 `storage/` 目录：
```
storage/
├── templates/      # 模板文件
├── uploads/        # 上传的临时文件
├── outputs/        # 生成的文档
├── exports/        # 批量导出的ZIP
└── database.db     # SQLite数据库
```

### 故障排查

#### 1. 检查容器健康状态
```bash
docker compose ps
docker inspect --format='{{json .State.Health}}' lesson-tools-backend
docker inspect --format='{{json .State.Health}}' lesson-tools-frontend
```

#### 2. 查看详细错误
```bash
docker compose logs backend --tail=100
docker compose logs frontend --tail=100
```

#### 3. 重启服务
```bash
docker compose restart
```

#### 4. 完全重新部署
```bash
docker compose down
docker compose up -d --build
```

### 端口配置

如需修改端口，编辑 `docker-compose.yml`：

```yaml
services:
  backend:
    ports:
      - "8001:8000"  # 主机端口:容器端口

  frontend:
    ports:
      - "8081:80"    # 主机端口:容器端口
```

修改后重启：
```bash
docker compose down
docker compose up -d
```

### 环境变量配置

环境变量在项目根目录的 `.env` 文件中配置：
```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key
```

修改后需重启容器：
```bash
docker compose restart backend
```

### 性能监控

```bash
# 查看资源使用情况
docker stats

# 查看特定容器资源使用
docker stats lesson-tools-backend lesson-tools-frontend
```

### 备份与恢复

#### 备份
```bash
# 备份整个storage目录
tar -czf backup-$(date +%Y%m%d).tar.gz storage/

# 仅备份数据库
cp storage/database.db storage/database.db.backup
```

#### 恢复
```bash
# 恢复storage目录
tar -xzf backup-20260106.tar.gz

# 恢复数据库
cp storage/database.db.backup storage/database.db
```

### 更新应用

```bash
# 1. 拉取最新代码
git pull

# 2. 停止服务
docker compose down

# 3. 重新构建
docker compose up -d --build

# 4. 查看日志确认
docker compose logs -f
```

---

**部署时间**: 2026-01-06
**Docker版本**: 29.1.2
**Docker Compose版本**: v5.0.0
