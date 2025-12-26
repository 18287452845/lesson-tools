#!/bin/bash

# 后台启动前后端项目
# 日志文件保存在 logs/ 目录

echo "正在后台启动 LessonTools 项目..."

# 创建日志目录
mkdir -p logs

# 检查是否已经在运行
if [ -f "logs/backend.pid" ]; then
    backend_pid=$(cat logs/backend.pid)
    if ps -p $backend_pid > /dev/null 2>&1; then
        echo "⚠ 后端已经在运行 (PID: $backend_pid)"
    else
        rm logs/backend.pid
    fi
fi

if [ -f "logs/frontend.pid" ]; then
    frontend_pid=$(cat logs/frontend.pid)
    if ps -p $frontend_pid > /dev/null 2>&1; then
        echo "⚠ 前端已经在运行 (PID: $frontend_pid)"
    else
        rm logs/frontend.pid
    fi
fi

# 启动后端
echo "启动后端服务..."
cd "$(dirname "$0")"
source venv/bin/activate

nohup python run_backend.py > logs/backend.log 2>&1 &
backend_pid=$!
echo $backend_pid > logs/backend.pid

echo "✓ 后端服务已启动 (PID: $backend_pid)"
echo "  日志文件: logs/backend.log"
echo "  访问地址: http://127.0.0.1:8000"
echo "  API文档: http://127.0.0.1:8000/docs"

# 等待后端启动
sleep 3

# 启动前端
echo ""
echo "启动前端服务..."
cd frontend

nohup npm run dev > ../logs/frontend.log 2>&1 &
frontend_pid=$!
echo $frontend_pid > ../logs/frontend.pid

cd ..

echo "✓ 前端服务已启动 (PID: $frontend_pid)"
echo "  日志文件: logs/frontend.log"
echo "  访问地址: http://localhost:5173"

echo ""
echo "==========================================="
echo "✓ 所有服务已启动成功！"
echo "==========================================="
echo ""
echo "访问应用："
echo "  前端: http://localhost:5173"
echo "  后端API: http://127.0.0.1:8000/docs"
echo ""
echo "查看日志："
echo "  后端: tail -f logs/backend.log"
echo "  前端: tail -f logs/frontend.log"
echo ""
echo "停止服务："
echo "  运行: ./stop.sh"
echo "  或运行: kill $(cat logs/backend.pid) $(cat logs/frontend.pid)"
echo ""
