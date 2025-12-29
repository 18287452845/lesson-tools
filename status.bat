@echo off
REM 检查服务状态 (Windows)

echo ==========================================
echo LessonTools 服务状态
echo ==========================================
echo.

REM 检查后端
echo 【后端服务】
if exist "logs\backend.pid" (
    set /p backend_pid=<logs\backend.pid
    tasklist /FI "PID eq %backend_pid%" 2>NUL | find /I /N "python.exe">NUL
    if "%ERRORLEVEL%"=="0" (
        echo   状态: ✓ 运行中
        echo   PID: %backend_pid%
        echo   地址: http://127.0.0.1:8000
        echo   API文档: http://127.0.0.1:8000/docs

        REM 检查端口
        netstat -an | findstr ":8000.*LISTENING" > nul
        if "%ERRORLEVEL%"=="0" (
            echo   端口: ✓ 8000已监听
        ) else (
            echo   端口: ⚠ 8000未监听
        )
    ) else (
        echo   状态: ✗ 未运行 ^(PID文件存在但进程不存在^)
        del logs\backend.pid
    )
) else (
    echo   状态: ✗ 未运行
)

echo.

REM 检查前端
echo 【前端服务】
if exist "logs\frontend.pid" (
    set /p frontend_pid=<logs\frontend.pid
    tasklist /FI "PID eq %frontend_pid%" 2>NUL | find /I /N "node.exe">NUL
    if "%ERRORLEVEL%"=="0" (
        echo   状态: ✓ 运行中
        echo   PID: %frontend_pid%
        echo   地址: http://localhost:5173

        REM 检查端口
        netstat -an | findstr ":5173.*LISTENING" > nul
        if "%ERRORLEVEL%"=="0" (
            echo   端口: ✓ 5173已监听
        ) else (
            echo   端口: ⚠ 5173未监听
        )
    ) else (
        echo   状态: ✗ 未运行 ^(PID文件存在但进程不存在^)
        del logs\frontend.pid
    )
) else (
    echo   状态: ✗ 未运行
)

echo.
echo 【日志文件】
if exist "logs\backend.log" (
    echo   后端日志: logs\backend.log
) else (
    echo   后端日志: 无
)

if exist "logs\frontend.log" (
    echo   前端日志: logs\frontend.log
) else (
    echo   前端日志: 无
)

echo.
echo 【快捷命令】
echo   启动服务: start.bat
echo   停止服务: stop.bat
echo   查看后端日志: type logs\backend.log
echo   查看前端日志: type logs\frontend.log
echo.

pause
