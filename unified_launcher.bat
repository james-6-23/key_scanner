@echo off
setlocal enabledelayedexpansion

REM ============================================
REM API密钥扫描器 - 统一启动脚本 (Windows版)
REM 支持本地环境和Docker容器两种部署方式
REM ============================================

REM 设置代码页为UTF-8
chcp 65001 >nul 2>&1

REM ============================================
REM 全局变量
REM ============================================
set "SCRIPT_DIR=%~dp0"
set "PROJECT_NAME=API Key Scanner"
set "LOG_FILE=%SCRIPT_DIR%launcher.log"
set "DEPLOYMENT_MODE="
set "PYTHON_CMD="
set "VENV_PATH=.venv"
set "DOCKER_AVAILABLE=0"
set "PYTHON_AVAILABLE=0"

REM 切换到脚本目录
cd /d "%SCRIPT_DIR%"

REM 清空日志文件
echo. > "%LOG_FILE%"
echo [%date% %time%] 统一启动器开始运行 >> "%LOG_FILE%"

REM ============================================
REM 主菜单
REM ============================================
:MAIN_MENU
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║         🔍 API密钥扫描器 - 统一启动器 🔍                  ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 欢迎使用API密钥扫描器统一启动器！
echo 本工具将帮助您选择合适的部署方式。
echo.

REM 检测可用环境
call :DETECT_ENVIRONMENTS

echo.
echo 请选择部署模式：
echo.
if "%DOCKER_AVAILABLE%"=="1" (
    echo   1) 🐳 Docker容器部署
    echo      推荐：隔离性好，配置简单，包含WARP代理
    echo.
) else (
    echo   1) 🐳 Docker容器部署 [不可用 - Docker未安装]
    echo.
)

if "%PYTHON_AVAILABLE%"=="1" (
    echo   2) 💻 本地环境部署
    echo      适合：开发调试，资源受限环境
    echo.
) else (
    echo   2) 💻 本地环境部署 [不可用 - Python未安装]
    echo.
)

echo   3) 📖 查看帮助文档
echo.
echo   4) 🔧 系统诊断
echo.
echo   5) 退出
echo.

set /p choice="请选择 [1-5]: "

if "%choice%"=="1" (
    if "%DOCKER_AVAILABLE%"=="1" (
        call :DEPLOY_DOCKER
    ) else (
        echo.
        echo [错误] Docker环境不可用
        echo 请先安装Docker Desktop for Windows
        pause
        goto MAIN_MENU
    )
) else if "%choice%"=="2" (
    if "%PYTHON_AVAILABLE%"=="1" (
        call :DEPLOY_LOCAL
    ) else (
        echo.
        echo [错误] Python环境不可用
        echo 请先安装Python 3.8或更高版本
        pause
        goto MAIN_MENU
    )
) else if "%choice%"=="3" (
    call :SHOW_HELP
    goto MAIN_MENU
) else if "%choice%"=="4" (
    call :RUN_DIAGNOSTICS
    goto MAIN_MENU
) else if "%choice%"=="5" (
    echo.
    echo 感谢使用，再见！
    exit /b 0
) else (
    echo.
    echo [错误] 无效的选择
    pause
    goto MAIN_MENU
)

goto MAIN_MENU

REM ============================================
REM 环境检测
REM ============================================
:DETECT_ENVIRONMENTS
echo [信息] 检测可用的部署环境...

REM 检测Docker
docker --version >nul 2>&1
if %errorlevel%==0 (
    set "DOCKER_AVAILABLE=1"
    echo [✓] Docker环境可用
    docker-compose --version >nul 2>&1
    if %errorlevel%==0 (
        echo [✓] Docker Compose可用
    ) else (
        docker compose version >nul 2>&1
        if %errorlevel%==0 (
            echo [✓] Docker Compose (插件模式) 可用
        ) else (
            set "DOCKER_AVAILABLE=0"
            echo [✗] Docker Compose不可用
        )
    )
) else (
    echo [✗] Docker未安装
)

REM 检测Python
python --version >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    set "PYTHON_AVAILABLE=1"
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [✓] Python可用 (版本: !PYTHON_VERSION!)
) else (
    python3 --version >nul 2>&1
    if %errorlevel%==0 (
        set "PYTHON_CMD=python3"
        set "PYTHON_AVAILABLE=1"
        for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
        echo [✓] Python3可用 (版本: !PYTHON_VERSION!)
    ) else (
        echo [✗] Python未安装
    )
)

exit /b 0

REM ============================================
REM Docker部署
REM ============================================
:DEPLOY_DOCKER
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              Docker容器部署模式                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 检查配置文件
call :CHECK_CONFIG_FILES
if %errorlevel% neq 0 (
    echo.
    set /p continue="配置文件需要更新，是否继续？(y/n): "
    if /i not "!continue!"=="y" (
        echo [信息] 已取消
        pause
        exit /b 0
    )
)

REM 检查是否有运行中的容器
docker-compose ps 2>nul | findstr "Up" >nul
if %errorlevel%==0 (
    echo.
    echo [警告] 检测到运行中的容器
    echo.
    echo 1) 重启服务
    echo 2) 查看日志
    echo 3) 停止服务
    echo 4) 返回
    echo.
    set /p docker_action="请选择操作 [1-4]: "
    
    if "!docker_action!"=="1" (
        echo [信息] 重启服务...
        docker-compose down
        docker-compose up -d
    ) else if "!docker_action!"=="2" (
        echo [信息] 查看日志（按Ctrl+C退出）...
        docker-compose logs -f
    ) else if "!docker_action!"=="3" (
        echo [信息] 停止服务...
        docker-compose down
    ) else if "!docker_action!"=="4" (
        exit /b 0
    )
) else (
    echo [信息] 拉取最新镜像...
    docker-compose pull
    
    echo [信息] 构建应用镜像...
    docker-compose build --no-cache scanner
    
    echo [信息] 启动服务...
    docker-compose up -d
    
    echo [信息] 等待服务启动...
    timeout /t 5 /nobreak >nul
    
    REM 检查服务状态
    docker-compose ps | findstr "Up" >nul
    if %errorlevel%==0 (
        echo.
        echo [✓] 服务启动成功！
        echo.
        echo 常用命令：
        echo   查看日志: docker-compose logs -f
        echo   停止服务: docker-compose down
        echo   重启服务: docker-compose restart
        echo   进入容器: docker exec -it key-scanner /bin/bash
        echo   健康检查: docker exec key-scanner python token_health_monitor.py github_tokens.txt
    ) else (
        echo [错误] 服务启动失败
        docker-compose logs --tail=50
    )
)

echo.
pause
exit /b 0

REM ============================================
REM 本地环境部署
REM ============================================
:DEPLOY_LOCAL
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              本地环境部署模式                              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 检查配置文件
call :CHECK_CONFIG_FILES
if %errorlevel% neq 0 (
    echo.
    set /p continue="配置文件需要更新，是否继续？(y/n): "
    if /i not "!continue!"=="y" (
        echo [信息] 已取消
        pause
        exit /b 0
    )
)

REM 创建/激活虚拟环境
if not exist "%VENV_PATH%" (
    echo [信息] 创建虚拟环境...
    %PYTHON_CMD% -m venv %VENV_PATH%
)

echo [信息] 激活虚拟环境...
if exist "%VENV_PATH%\Scripts\activate.bat" (
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo [错误] 无法激活虚拟环境
    pause
    exit /b 1
)

REM 检查UV
where uv >nul 2>&1
if %errorlevel%==0 (
    echo [信息] 使用UV安装依赖（速度更快）...
    uv pip install -r requirements.txt
) else (
    echo [信息] 使用pip安装依赖...
    pip install -r requirements.txt
)

echo.
echo [✓] 环境准备完成！
echo.
echo 请选择运行模式：
echo 1) 运行主扫描器
echo 2) 运行Token健康监控
echo 3) 显示运行命令
echo 4) 返回
echo.
set /p run_mode="请选择 [1-4]: "

if "%run_mode%"=="1" (
    echo [信息] 启动主扫描器...
    python app\api_key_scanner.py
) else if "%run_mode%"=="2" (
    if exist "github_tokens.txt" (
        echo [信息] 启动Token健康监控...
        python token_health_monitor.py github_tokens.txt
    ) else (
        echo [错误] github_tokens.txt文件不存在
    )
) else if "%run_mode%"=="3" (
    echo.
    echo 运行命令：
    echo   激活环境: %VENV_PATH%\Scripts\activate.bat
    echo   运行扫描器: python app\api_key_scanner.py
    echo   运行监控: python token_health_monitor.py github_tokens.txt
    echo   退出环境: deactivate
) else if "%run_mode%"=="4" (
    deactivate 2>nul
    exit /b 0
)

echo.
pause
deactivate 2>nul
exit /b 0

REM ============================================
REM 检查配置文件
REM ============================================
:CHECK_CONFIG_FILES
echo [信息] 检查配置文件...

set "config_ok=1"

REM 检查.env文件
if not exist ".env" (
    if exist ".env.docker" (
        echo [信息] 使用.env.docker作为模板
        copy ".env.docker" ".env" >nul
    ) else if exist "env.example" (
        echo [信息] 使用env.example作为模板
        copy "env.example" ".env" >nul
    ) else (
        echo [错误] .env配置文件不存在
        set "config_ok=0"
    )
) else (
    echo [✓] .env配置文件已存在
)

REM 检查queries.txt
if not exist "queries.txt" (
    if exist "queries.example" (
        echo [信息] 使用queries.example作为模板
        copy "queries.example" "queries.txt" >nul
    ) else (
        echo [错误] queries.txt文件不存在
        set "config_ok=0"
    )
) else (
    echo [✓] queries.txt文件已存在
)

REM 检查GitHub tokens
if exist ".env" (
    findstr "ghp_your_token_here" ".env" >nul 2>&1
    if %errorlevel%==0 (
        echo [警告] 检测到示例Token，请配置真实的GitHub Token
        set "config_ok=0"
    )
    
    findstr "USE_EXTERNAL_TOKEN_FILE=true" ".env" >nul 2>&1
    if %errorlevel%==0 (
        if not exist "github_tokens.txt" (
            echo [警告] 配置使用外部Token文件，但github_tokens.txt不存在
            if exist "github_tokens.example" (
                echo [信息] 使用github_tokens.example作为模板
                copy "github_tokens.example" "github_tokens.txt" >nul
            )
        )
    )
)

if "%config_ok%"=="1" (
    exit /b 0
) else (
    exit /b 1
)

REM ============================================
REM 显示帮助
REM ============================================
:SHOW_HELP
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                      帮助文档                              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 📚 部署模式说明：
echo.
echo 1. Docker容器部署
echo    - 优点：环境隔离、配置简单、包含代理
echo    - 缺点：需要Docker环境、资源占用较高
echo    - 适用：生产环境、VPS服务器
echo.
echo 2. 本地环境部署
echo    - 优点：资源占用低、便于调试
echo    - 缺点：需要配置Python环境、可能有依赖冲突
echo    - 适用：开发环境、本地测试
echo.
echo 📝 配置文件说明：
echo    .env - 环境变量配置
echo    queries.txt - 搜索查询配置
echo    github_tokens.txt - GitHub Token列表（可选）
echo.
echo 🔗 相关文档：
echo    README.md - 项目说明
echo    DOCKER_DEPLOY_GUIDE.md - Docker部署指南
echo    DEPLOYMENT_GUIDE.md - 综合部署指南
echo.
pause
exit /b 0

REM ============================================
REM 系统诊断
REM ============================================
:RUN_DIAGNOSTICS
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                      系统诊断                              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 🔍 正在进行系统诊断...
echo.

echo 系统信息:
echo   操作系统: Windows
echo   主机名: %COMPUTERNAME%
echo   当前用户: %USERNAME%
echo   工作目录: %CD%
echo.

echo Docker环境:
docker --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=3" %%i in ('docker --version 2^>^&1') do echo   Docker: %%i
    docker info >nul 2>&1
    if %errorlevel%==0 (
        echo   状态: 运行中
    ) else (
        echo   状态: 未运行
    )
) else (
    echo   Docker: 未安装
)

docker-compose --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=3" %%i in ('docker-compose --version 2^>^&1') do echo   Docker Compose: %%i
) else (
    echo   Docker Compose: 未安装
)
echo.

echo Python环境:
python --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do echo   Python: %%i
)
python3 --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do echo   Python3: %%i
)
pip --version >nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=2" %%i in ('pip --version 2^>^&1') do echo   pip: %%i
)
where uv >nul 2>&1
if %errorlevel%==0 (
    echo   UV: 已安装
)
echo.

echo 配置文件:
for %%f in (.env queries.txt github_tokens.txt requirements.txt docker-compose.yml) do (
    if exist "%%f" (
        for /f %%i in ('find /c /v "" ^< "%%f"') do echo   ✓ %%f [%%i 行]
    ) else (
        echo   ✗ %%f
    )
)
echo.

echo 数据目录:
if exist "data" (
    echo   data\: 存在
    dir /b "data\keys" 2>nul | find /c /v "" >temp.txt
    set /p keys_count=<temp.txt
    echo     - keys\: !keys_count! 个文件
    dir /b "data\logs" 2>nul | find /c /v "" >temp.txt
    set /p logs_count=<temp.txt
    echo     - logs\: !logs_count! 个文件
    del temp.txt 2>nul
) else (
    echo   data\: 不存在
)
echo.

pause
exit /b 0

REM ============================================
REM 脚本结束
REM ============================================
:END
endlocal
exit /b 0