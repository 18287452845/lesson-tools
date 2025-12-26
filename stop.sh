#!/bin/bash

# 停止前后端服务

echo "正在停止 LessonTools 服务..."

# 停止后端
if [ -f "logs/backend.pid" ]; then
    backend_pid=$(cat logs/backend.pid)
    if ps -p $backend_pid > /dev/null 2>&1; then
        kill $backend_pid
        echo "✓ 后端服务已停止 (PID: $backend_pid)"
        rm logs/backend.pid
    else
        echo "⚠ 后端服务未运行"
        rm logs/backend.pid
    fi
else
    echo "⚠ 未找到后端PID文件"
fi

# 停止前端
if [ -f "logs/frontend.pid" ]; then
    frontend_pid=$(cat logs/frontend.pid)
    if ps -p $frontend_pid > /dev/null 2>&1; then
        kill $frontend_pid
        echo "✓ 前端服务已停止 (PID: $frontend_pid)"
        rm logs/frontend.pid
    else
        echo "⚠ 前端服务未运行"
        rm logs/frontend.pid
    fi
else
    echo "⚠ 未找到前端PID文件"
fi

# 清理可能的遗留进程
echo ""
echo "清理遗留进程..."

# 清理后端进程
backend_pids=$(ps aux | grep "run_backend.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$backend_pids" ]; then
    echo "发现遗留的后端进程: $backend_pids"
    kill $backend_pids 2>/dev/null
fi

# 清理前端进程
frontend_pids=$(ps aux | grep "vite" | grep -v grep | awk '{print $2}')
if [ ! -z "$frontend_pids" ]; then
    echo "发现遗留的前端进程: $frontend_pids"
    kill $frontend_pids 2>/dev/null
fi

echo ""
echo "✓ 所有服务已停止"
