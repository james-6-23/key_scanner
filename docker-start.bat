@echo off
setlocal enabledelayedexpansion

REM ============================================
REM Docker快速启动脚本 - 超级版API密钥扫描器
REM Windows批处理版本
REM ============================================

REM 设置控制台编码为UTF-8
chcp 65001 >nul 2>&1

REM 颜色代码
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "PURPLE=[95m"
set "CYAN=[96m"
set "NC=[0m"

REM 显示标题
:show_banner
cls
echo %CYAN%
echo ╔══════════════════════════════════════════════════════════╗
echo ║         🚀 超级版API密钥扫描器 - Docker部署工具 🚀         ║
echo ╚══════════════════════════════════════════════════════════╝
echo %NC%
echo.

REM 检查参数
if "%1"=="" goto :menu
if "%1"=="start" goto :start
if "%1"=="stop" goto :stop
if "%1"=="restart" goto :restart
if "%1"=="build" goto :build
if "%1"=="logs" goto :logs
if "%1"=="status" goto :status
if "%1"=="clean" goto :clean
if "%1"=="update" goto :update
if "%1"=="launcher" goto :launcher
if "%1"=="scan" goto :scan
if "%1"=="help" goto :help
if "%1"=="/?" goto :help
if "%1"=="-h" goto :help
if "%1"=="--help" goto :help

echo %RED%[ERROR]%NC% 未知命令: %1
echo 使用 'docker-start.bat help' 查看帮助
exit /b 1

REM ============================================
REM 功能实现
REM ============================================

:check_docker
echo %BLUE%[INFO]%NC% 检查Docker环境...
docker --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Docker未安装！请先安装Docker Desktop。
    echo 访问 https://docs.docker.com/desktop/install/windows-install/ 获取安装指南
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Docker Compose未安装！
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%NC% Docker服务未运行！请启动Docker Desktop。
    exit /b 1
)

echo %GREEN%[SUCCESS]%NC% Docker环境检查通过
goto :eof

:init_config
echo %BLUE%[INFO]%NC% 初始化配置文件...

REM 创建.env文件
if not exist .env (
    if exist env.example (
        copy env.example .env >nul
        echo %GREEN%[SUCCESS]%NC% 已创建.env配置文件
        echo %YELLOW%[WARNING]%NC% 请编辑.env文件配置您的API密钥和其他设置
    ) else (
        echo %YELLOW%[WARNING]%NC% env.example不存在，创建默认.env文件
        (
            echo # ========== 基础配置 ==========
            echo DEFAULT_API_TYPE=gemini
            echo SCAN_API_TYPES=gemini
            echo.
            echo # ========== 代理配置 ==========
            echo PROXY=http://warp:1080
            echo.
            echo # ========== 凭证管理 ==========
            echo USE_CREDENTIAL_MANAGER=true
            echo CREDENTIAL_AUTO_HARVEST=false
            echo CREDENTIAL_STORAGE_TYPE=redis
            echo.
            echo # ========== 负载均衡 ==========
            echo LOAD_BALANCE_STRATEGY=adaptive
            echo.
            echo # ========== 监控配置 ==========
            echo ENABLE_MONITORING=true
            echo MONITORING_INTERVAL=300
            echo.
            echo # ========== 性能优化 ==========
            echo HAJIMI_MAX_WORKERS=10
            echo HAJIMI_BATCH_SIZE=10
            echo HAJIMI_BATCH_INTERVAL=60
        ) > .env
        echo %GREEN%[SUCCESS]%NC% 已创建默认.env文件
    )
) else (
    echo %BLUE%[INFO]%NC% .env文件已存在
)

REM 创建queries.txt文件
if not exist queries.txt (
    if exist queries.example (
        copy queries.example queries.txt >nul
        echo %GREEN%[SUCCESS]%NC% 已创建queries.txt文件
    ) else (
        echo test query > queries.txt
        echo %YELLOW%[WARNING]%NC% 已创建默认queries.txt文件，请添加您的查询
    )
) else (
    echo %BLUE%[INFO]%NC% queries.txt文件已存在
)

REM 创建github_tokens.txt文件
if not exist github_tokens.txt (
    type nul > github_tokens.txt
    echo %BLUE%[INFO]%NC% 已创建空的github_tokens.txt文件
)

REM 创建必要的目录
if not exist logs mkdir logs
if not exist monitoring mkdir monitoring
if not exist config\queries mkdir config\queries
echo %GREEN%[SUCCESS]%NC% 目录结构创建完成
goto :eof

:start
call :show_banner
call :check_docker
call :init_config
echo %BLUE%[INFO]%NC% 启动服务...
docker-compose up -d
if errorlevel 1 (
    echo %RED%[ERROR]%NC% 服务启动失败
    exit /b 1
)
echo %GREEN%[SUCCESS]%NC% 服务启动完成
timeout /t 5 /nobreak >nul
call :show_info
goto :end

:stop
echo %BLUE%[INFO]%NC% 停止服务...
docker-compose down
echo %GREEN%[SUCCESS]%NC% 服务已停止
goto :end

:restart
call :stop
call :start
goto :end

:build
echo %BLUE%[INFO]%NC% 构建Docker镜像...
docker-compose build --no-cache
echo %GREEN%[SUCCESS]%NC% 镜像构建完成
goto :end

:logs
docker-compose logs -f --tail=100
goto :end

:status
docker-compose ps
goto :end

:clean
echo %YELLOW%[WARNING]%NC% 清理所有数据...
set /p confirm="确定要清理所有数据吗？这将删除所有扫描结果和缓存！(y/N) "
if /i "%confirm%"=="y" (
    docker-compose down -v
    if exist logs\* del /q logs\*
    if exist monitoring\* del /q monitoring\*
    echo %GREEN%[SUCCESS]%NC% 数据清理完成
) else (
    echo %BLUE%[INFO]%NC% 取消清理操作
)
goto :end

:update
echo %BLUE%[INFO]%NC% 更新系统...
git pull origin main
docker-compose build --no-cache
docker-compose up -d
echo %GREEN%[SUCCESS]%NC% 系统更新完成
goto :end

:launcher
docker-compose exec scanner python scanner_launcher.py
goto :end

:scan
shift
set args=
:scan_loop
if "%1"=="" goto :scan_exec
set args=%args% %1
shift
goto :scan_loop
:scan_exec
docker-compose exec scanner python app/api_key_scanner_super.py %args%
goto :end

:show_info
echo.
echo %GREEN%════════════════════════════════════════════════════════%NC%
echo %GREEN%服务已成功启动！%NC%
echo %GREEN%════════════════════════════════════════════════════════%NC%
echo.
echo %CYAN%📊 服务状态:%NC%
docker-compose ps
echo.
echo %CYAN%🔧 管理命令:%NC%
echo   查看日志:     docker-compose logs -f scanner
echo   进入启动器:   docker-compose exec scanner python scanner_launcher.py
echo   快速扫描:     docker-compose exec scanner python app/api_key_scanner_super.py
echo   停止服务:     docker-compose down
echo   重启服务:     docker-compose restart
echo.
echo %CYAN%🌐 Web界面:%NC%
echo   监控面板:     http://localhost:8080
echo.
echo %CYAN%📁 数据位置:%NC%
echo   扫描结果:     .\logs\
echo   监控数据:     .\monitoring\
echo.
goto :eof

:help
echo 使用方法: docker-start.bat [命令]
echo.
echo 命令:
echo   start     - 启动服务
echo   stop      - 停止服务
echo   restart   - 重启服务
echo   build     - 构建镜像
echo   logs      - 查看日志
echo   status    - 查看状态
echo   clean     - 清理数据
echo   update    - 更新系统
echo   launcher  - 进入启动器
echo   scan      - 执行扫描
echo   help      - 显示帮助
echo.
echo 不带参数运行将显示交互式菜单
goto :end

REM ============================================
REM 交互式菜单
REM ============================================

:menu
call :show_banner
call :check_docker

:menu_loop
echo.
echo %PURPLE%请选择操作:%NC%
echo   1) 🚀 快速启动（推荐）
echo   2) 🔨 重新构建并启动
echo   3) 📊 查看服务状态
echo   4) 📝 查看日志
echo   5) 🎮 进入交互式启动器
echo   6) ⚡ 执行快速扫描
echo   7) 🛑 停止服务
echo   8) 🧹 清理数据
echo   9) 🔄 更新系统
echo   0) 退出
echo.
set /p choice="请输入选项 [0-9]: "

if "%choice%"=="1" (
    call :init_config
    call :start_services
    call :show_info
) else if "%choice%"=="2" (
    call :init_config
    call :build
    call :start_services
    call :show_info
) else if "%choice%"=="3" (
    docker-compose ps
) else if "%choice%"=="4" (
    docker-compose logs -f --tail=100
) else if "%choice%"=="5" (
    docker-compose exec scanner python scanner_launcher.py
) else if "%choice%"=="6" (
    docker-compose exec scanner python app/api_key_scanner_super.py
) else if "%choice%"=="7" (
    call :stop
) else if "%choice%"=="8" (
    call :clean
) else if "%choice%"=="9" (
    call :update
) else if "%choice%"=="0" (
    echo %BLUE%[INFO]%NC% 退出
    goto :end
) else (
    echo %RED%[ERROR]%NC% 无效选项
)

goto :menu_loop

:start_services
echo %BLUE%[INFO]%NC% 启动服务...
docker-compose up -d
if errorlevel 1 (
    echo %RED%[ERROR]%NC% 服务启动失败
    pause
    goto :menu_loop
)
echo %GREEN%[SUCCESS]%NC% 服务启动完成
timeout /t 5 /nobreak >nul
docker-compose ps
goto :eof

:end
endlocal
exit /b 0