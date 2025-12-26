#!/bin/bash

# 检查服务状态

echo "==========================================="
echo "LessonTools 服务状态"
echo "==========================================="
echo ""

# 检查后端
echo "【后端服务】"
if [ -f "logs/backend.pid" ]; then
    backend_pid=$(cat logs/backend.pid)
    if ps -p $backend_pid > /dev/null 2>&1; then
        echo "  状态: ✓ 运行中"
        echo "  PID: $backend_pid"
        echo "  地址: http://127.0.0.1:8000"
        echo "  API文档: http://127.0.0.1:8000/docs"

        # 检查端口
        if netstat -tuln 2>/dev/null | grep -q ":8000 "; then
            echo "  端口: ✓ 8000已监听"
        else
            echo "  端口: ⚠ 8000未监听"
        fi
    else
        echo "  状态: ✗ 未运行 (PID文件存在但进程不存在)"
        rm logs/backend.pid
    fi
else
    echo "  状态: ✗ 未运行"
fi

echo ""

# 检查前端
echo "【前端服务】"
if [ -f "logs/frontend.pid" ]; then
    frontend_pid=$(cat logs/frontend.pid)
    if ps -p $frontend_pid > /dev/null 2>&1; then
        echo "  状态: ✓ 运行中"
        echo "  PID: $frontend_pid"
        echo "  地址: http://localhost:5173"

        # 检查端口
        if netstat -tuln 2>/dev/null | grep -q ":5173 "; then
            echo "  端口: ✓ 5173已监听"
        else
            echo "  端口: ⚠ 5173未监听"
        fi
    else
        echo "  状态: ✗ 未运行 (PID文件存在但进程不存在)"
        rm logs/frontend.pid
    fi
else
    echo "  状态: ✗ 未运行"
fi

echo ""
echo "【日志文件】"
if [ -f "logs/backend.log" ]; then
    backend_log_size=$(du -h logs/backend.log | cut -f1)
    backend_log_lines=$(wc -l < logs/backend.log)
    echo "  后端日志: logs/backend.log ($backend_log_size, $backend_log_lines 行)"
else
    echo "  后端日志: 无"
fi

if [ -f "logs/frontend.log" ]; then
    frontend_log_size=$(du -h logs/frontend.log | cut -f1)
    frontend_log_lines=$(wc -l < logs/frontend.log)
    echo "  前端日志: logs/frontend.log ($frontend_log_size, $frontend_log_lines 行)"
else
    echo "  前端日志: 无"
fi

echo ""
echo "【快捷命令】"
echo "  启动服务: ./start.sh"
echo "  停止服务: ./stop.sh"
echo "  查看后端日志: tail -f logs/backend.log"
echo "  查看前端日志: tail -f logs/frontend.log"
echo ""
