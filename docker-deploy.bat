@echo off
REM Docker 快速部署脚本 (Windows)
REM 用于一键启动智能教案助手 Docker 服务

setlocal enabledelayedexpansion

echo ======================================
echo   智能教案助手 Docker 快速部署
echo ======================================
echo.

REM 检查Docker是否安装
echo [信息] 检查 Docker 环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Docker，请先安装 Docker
    echo 安装指南: https://docs.docker.com/get-docker/
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Docker Compose，请先安装 Docker Compose
    echo 安装指南: https://docs.docker.com/compose/install/
    pause
    exit /b 1
)

echo [成功] Docker 环境检查通过
docker --version
docker-compose --version
echo.

REM 检查.env文件
echo [信息] 检查环境配置...
if not exist .env (
    echo [警告] .env 文件不存在，正在从 .env.example 创建...
    if exist .env.example (
        copy .env.example .env >nul
        echo [警告] 请编辑 .env 文件并填入您的 API 密钥
        echo   notepad .env
        echo.
        echo 必填项：
        echo   - AI_PROVIDER=deepseek
        echo   - DEEPSEEK_API_KEY=sk-your-api-key
        echo.
        pause
    ) else (
        echo [错误] .env.example 文件不存在
        pause
        exit /b 1
    )
)

REM 简单检查API密钥
findstr /C:"DEEPSEEK_API_KEY=sk-" .env >nul 2>&1
if %errorlevel% neq 0 (
    findstr /C:"ANTHROPIC_API_KEY=sk-" .env >nul 2>&1
    if %errorlevel% neq 0 (
        echo [错误] 未检测到有效的 API 密钥，请在 .env 文件中配置
        pause
        exit /b 1
    )
)

echo [成功] 环境配置检查通过
echo.

REM 创建必要的目录
echo [信息] 创建存储目录...
if not exist storage\templates mkdir storage\templates
if not exist storage\uploads mkdir storage\uploads
if not exist storage\outputs mkdir storage\outputs
if not exist storage\exports mkdir storage\exports
echo [成功] 存储目录创建完成
echo.

REM 构建并启动服务
echo [信息] 构建并启动 Docker 服务...
if "%1"=="--build" (
    echo [信息] 强制重新构建镜像...
    docker-compose up -d --build
) else (
    docker-compose up -d
)

if %errorlevel% neq 0 (
    echo [错误] Docker 服务启动失败
    pause
    exit /b 1
)

echo [成功] Docker 服务已启动
echo.

REM 等待服务就绪
echo [信息] 等待服务启动...
set attempts=0
set max_attempts=30

:wait_loop
if %attempts% geq %max_attempts% goto wait_timeout

REM 检查后端健康状态
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 goto services_ready

set /a attempts+=1
echo|set /p=.
timeout /t 2 /nobreak >nul
goto wait_loop

:wait_timeout
echo.
echo [警告] 后端服务启动超时，请检查日志
echo [信息] 查看日志命令: docker-compose logs -f backend
goto show_info

:services_ready
echo.
echo [成功] 后端服务已就绪
echo.

:show_info
echo ======================================
echo [成功] 部署完成！
echo ======================================
echo.
echo 访问地址：
echo   前端界面: http://localhost
echo   后端API:  http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo.
echo 常用命令：
echo   查看日志: docker-compose logs -f
echo   查看状态: docker-compose ps
echo   停止服务: docker-compose stop
echo   重启服务: docker-compose restart
echo   完全清理: docker-compose down -v
echo.
pause
