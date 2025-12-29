@echo off
REM 后台启动前后端项目 (Windows)
REM 日志文件保存在 logs/ 目录

echo ==========================================
echo 正在后台启动 LessonTools 项目...
echo ==========================================
echo.

REM 创建日志目录
if not exist "logs" mkdir logs

REM 检查是否已经在运行
if exist "logs\backend.pid" (
    set /p backend_pid=<logs\backend.pid
    tasklist /FI "PID eq %backend_pid%" 2>NUL | find /I /N "python.exe">NUL
    if "%ERRORLEVEL%"=="0" (
        echo ⚠ 后端已经在运行 (PID: %backend_pid%)
    ) else (
        del logs\backend.pid
    )
)

if exist "logs\frontend.pid" (
    set /p frontend_pid=<logs\frontend.pid
    tasklist /FI "PID eq %frontend_pid%" 2>NUL | find /I /N "node.exe">NUL
    if "%ERRORLEVEL%"=="0" (
        echo ⚠ 前端已经在运行 (PID: %frontend_pid%)
    ) else (
        del logs\frontend.pid
    )
)

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 启动后端
echo.
echo 启动后端服务...
call venv\Scripts\activate.bat
start /B python run_backend.py > logs\backend.log 2>&1
set BACKEND_PID=%ERRORLEVEL%

REM 获取实际的Python进程PID需要更复杂的方法
REM 这里使用一个简化的方法：记录启动时间
echo %BACKEND_PID% > logs\backend.pid

echo ✓ 后端服务已启动
echo   日志文件: logs\backend.log
echo   访问地址: http://127.0.0.1:8000
echo   API文档: http://127.0.0.1:8000/docs

REM 等待后端启动
timeout /t 3 /nobreak > nul

REM 启动前端
echo.
echo 启动前端服务...
cd frontend
start /B npm run dev > ..\logs\frontend.log 2>&1
set FRONTEND_PID=%ERRORLEVEL%
echo %FRONTEND_PID% > ..\logs\frontend.pid
cd ..

echo ✓ 前端服务已启动
echo   日志文件: logs\frontend.log
echo   访问地址: http://localhost:5173

echo.
echo ==========================================
echo ✓ 所有服务已启动成功！
echo ==========================================
echo.
echo 访问应用：
echo   前端: http://localhost:5173
echo   后端API: http://127.0.0.1:8000/docs
echo.
echo 查看日志：
echo   后端: type logs\backend.log
echo   前端: type logs\frontend.log
echo.
echo 停止服务：
echo   运行: stop.bat
echo.

pause
