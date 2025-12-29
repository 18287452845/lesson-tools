@echo off
REM 停止前后端服务 (Windows)

echo 正在停止 LessonTools 服务...
echo.

REM 停止后端
if exist "logs\backend.pid" (
    set /p backend_pid=<logs\backend.pid
    tasklist /FI "PID eq %backend_pid%" 2>NUL | find /I /N "python.exe">NUL
    if "%ERRORLEVEL%"=="0" (
        taskkill /PID %backend_pid% /F > nul 2>&1
        echo ✓ 后端服务已停止 ^(PID: %backend_pid%^)
        del logs\backend.pid
    ) else (
        echo ⚠ 后端服务未运行
        del logs\backend.pid
    )
) else (
    echo ⚠ 未找到后端PID文件
)

REM 停止前端
if exist "logs\frontend.pid" (
    set /p frontend_pid=<logs\frontend.pid
    tasklist /FI "PID eq %frontend_pid%" 2>NUL | find /I /N "node.exe">NUL
    if "%ERRORLEVEL%"=="0" (
        taskkill /PID %frontend_pid% /F > nul 2>&1
        echo ✓ 前端服务已停止 ^(PID: %frontend_pid%^)
        del logs\frontend.pid
    ) else (
        echo ⚠ 前端服务未运行
        del logs\frontend.pid
    )
) else (
    echo ⚠ 未找到前端PID文件
)

REM 清理可能的遗留进程
echo.
echo 清理遗留进程...

REM 清理后端进程 (查找所有run_backend.py进程)
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" ^| find "run_backend.py"') do (
    if not "%%a"=="" (
        echo 发现遗留的后端进程: %%a
        taskkill /PID %%a /F > nul 2>&1
    )
)

REM 清理前端进程 (Vite)
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" ^| find "vite"') do (
    if not "%%a"=="" (
        echo 发现遗留的前端进程: %%a
        taskkill /PID %%a /F > nul 2>&1
    )
)

echo.
echo ✓ 所有服务已停止
echo.

pause
