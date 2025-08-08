#!/bin/bash

# ============================================
# API密钥扫描器 - 统一启动脚本
# 支持本地环境和Docker容器两种部署方式
# ============================================

set -e

# ============================================
# 颜色定义
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ============================================
# 全局变量
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="API Key Scanner"
LOG_FILE="${SCRIPT_DIR}/launcher.log"
DEPLOYMENT_MODE=""
PYTHON_CMD=""
VENV_PATH=".venv"

# ============================================
# 日志函数
# ============================================
log_to_file() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}${BLUE}$1${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    log_to_file "INFO: $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    log_to_file "SUCCESS: $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
    log_to_file "WARNING: $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
    log_to_file "ERROR: $1"
}

print_step() {
    echo -e "${PURPLE}[→]${NC} $1"
    log_to_file "STEP: $1"
}

# ============================================
# 系统检测函数
# ============================================
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

detect_python() {
    # 检测Python命令
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        return 1
    fi
    
    # 检查Python版本
    local version=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null)
    if [[ -z "$version" ]]; then
        return 1
    fi
    
    # 检查版本是否>=3.8
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    
    if [[ $major -lt 3 ]] || [[ $major -eq 3 && $minor -lt 8 ]]; then
        print_warning "Python版本过低 ($version)，需要3.8或更高版本"
        return 1
    fi
    
    print_success "检测到Python $version ($PYTHON_CMD)"
    return 0
}

# ============================================
# Docker环境检测
# ============================================
check_docker_prerequisites() {
    print_step "检查Docker环境..."
    
    local docker_available=true
    local compose_available=true
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker未安装"
        docker_available=false
    else
        if ! docker info &> /dev/null; then
            print_warning "Docker服务未运行"
            docker_available=false
        else
            local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
            print_success "Docker已安装 (版本: $docker_version)"
        fi
    fi
    
    # 检查Docker Compose
    if command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        print_success "Docker Compose已安装 (版本: $compose_version)"
    elif docker compose version &> /dev/null; then
        print_success "Docker Compose (插件模式) 已安装"
    else
        print_warning "Docker Compose未安装"
        compose_available=false
    fi
    
    if [[ "$docker_available" == true ]] && [[ "$compose_available" == true ]]; then
        return 0
    else
        return 1
    fi
}

# ============================================
# 本地环境检测
# ============================================
check_local_prerequisites() {
    print_step "检查本地Python环境..."
    
    # 检查Python
    if ! detect_python; then
        print_error "未找到合适的Python环境"
        return 1
    fi
    
    # 检查pip
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        print_warning "pip未安装，尝试安装..."
        $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || {
            print_error "无法安装pip"
            return 1
        }
    fi
    
    # 检查虚拟环境
    if [[ -d "$VENV_PATH" ]]; then
        print_success "发现现有虚拟环境"
    else
        print_info "虚拟环境未创建（将在启动时创建）"
    fi
    
    # 检查UV（可选）
    if command -v uv &> /dev/null; then
        print_success "UV包管理器已安装（将使用UV加速）"
    else
        print_info "UV未安装（将使用标准pip）"
    fi
    
    return 0
}

# ============================================
# 配置文件检查
# ============================================
check_config_files() {
    print_step "检查配置文件..."
    
    local config_ok=true
    
    # 检查.env文件
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.docker" ]]; then
            print_info "将使用.env.docker作为模板"
            cp .env.docker .env
        elif [[ -f "env.example" ]]; then
            print_info "将使用env.example作为模板"
            cp env.example .env
        else
            print_error ".env配置文件不存在"
            config_ok=false
        fi
    else
        print_success ".env配置文件已存在"
    fi
    
    # 检查queries.txt
    if [[ ! -f "queries.txt" ]]; then
        if [[ -f "queries.example" ]]; then
            print_info "将使用queries.example作为模板"
            cp queries.example queries.txt
        else
            print_error "queries.txt文件不存在"
            config_ok=false
        fi
    else
        print_success "queries.txt文件已存在"
    fi
    
    # 检查GitHub tokens配置
    if [[ -f ".env" ]]; then
        if grep -q "ghp_your_token_here\|github_pat_your_token" .env; then
            print_warning "检测到示例Token，请配置真实的GitHub Token"
            config_ok=false
        fi
        
        # 检查是否使用外部token文件
        if grep -q "USE_EXTERNAL_TOKEN_FILE=true" .env; then
            if [[ ! -f "github_tokens.txt" ]]; then
                print_warning "配置使用外部Token文件，但github_tokens.txt不存在"
                if [[ -f "github_tokens.example" ]]; then
                    print_info "将使用github_tokens.example作为模板"
                    cp github_tokens.example github_tokens.txt
                fi
            fi
        fi
    fi
    
    if [[ "$config_ok" == true ]]; then
        return 0
    else
        return 1
    fi
}

# ============================================
# Docker部署函数
# ============================================
deploy_with_docker() {
    print_header "Docker容器部署模式"
    
    # 检查Docker环境
    if ! check_docker_prerequisites; then
        print_error "Docker环境不满足要求"
        return 1
    fi
    
    # 检查配置文件
    if ! check_config_files; then
        print_warning "配置文件需要更新"
        echo ""
        read -p "是否继续？(y/n): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "已取消"
            return 1
        fi
    fi
    
    # 检查是否有运行中的容器
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        print_warning "检测到运行中的容器"
        echo "1) 重启服务"
        echo "2) 查看日志"
        echo "3) 停止服务"
        echo "4) 返回"
        read -p "请选择操作 [1-4]: " docker_action
        
        case $docker_action in
            1)
                print_step "重启服务..."
                docker-compose down
                docker-compose up -d
                ;;
            2)
                print_step "查看日志（按Ctrl+C退出）..."
                docker-compose logs -f
                ;;
            3)
                print_step "停止服务..."
                docker-compose down
                ;;
            4)
                return 0
                ;;
            *)
                print_error "无效选择"
                return 1
                ;;
        esac
    else
        # 启动新服务
        print_step "拉取最新镜像..."
        docker-compose pull
        
        print_step "构建应用镜像..."
        docker-compose build --no-cache scanner
        
        print_step "启动服务..."
        docker-compose up -d
        
        print_step "等待服务启动..."
        sleep 5
        
        # 检查服务状态
        if docker-compose ps | grep -q "Up"; then
            print_success "服务启动成功！"
            
            echo ""
            print_info "常用命令："
            echo "  查看日志: docker-compose logs -f"
            echo "  停止服务: docker-compose down"
            echo "  重启服务: docker-compose restart"
            echo "  进入容器: docker exec -it key-scanner /bin/bash"
            echo "  健康检查: docker exec key-scanner python token_health_monitor.py github_tokens.txt"
        else
            print_error "服务启动失败"
            docker-compose logs --tail=50
            return 1
        fi
    fi
    
    return 0
}

# ============================================
# 本地环境部署函数
# ============================================
deploy_local() {
    print_header "本地环境部署模式"
    
    # 检查Python环境
    if ! check_local_prerequisites; then
        print_error "本地环境不满足要求"
        return 1
    fi
    
    # 检查配置文件
    if ! check_config_files; then
        print_warning "配置文件需要更新"
        echo ""
        read -p "是否继续？(y/n): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "已取消"
            return 1
        fi
    fi
    
    # 创建/激活虚拟环境
    if [[ ! -d "$VENV_PATH" ]]; then
        print_step "创建虚拟环境..."
        $PYTHON_CMD -m venv $VENV_PATH
    fi
    
    # 激活虚拟环境
    print_step "激活虚拟环境..."
    if [[ -f "$VENV_PATH/bin/activate" ]]; then
        source $VENV_PATH/bin/activate
    elif [[ -f "$VENV_PATH/Scripts/activate" ]]; then
        source $VENV_PATH/Scripts/activate
    else
        print_error "无法激活虚拟环境"
        return 1
    fi
    
    # 安装依赖
    print_step "安装项目依赖..."
    if command -v uv &> /dev/null; then
        print_info "使用UV安装依赖（速度更快）..."
        uv pip install -r requirements.txt
    else
        print_info "使用pip安装依赖..."
        pip install -r requirements.txt
    fi
    
    # 提供运行选项
    echo ""
    print_success "环境准备完成！"
    echo ""
    echo "请选择运行模式："
    echo "1) 运行主扫描器"
    echo "2) 运行Token健康监控"
    echo "3) 运行两者（后台）"
    echo "4) 仅显示命令"
    read -p "请选择 [1-4]: " run_mode
    
    case $run_mode in
        1)
            print_step "启动主扫描器..."
            python app/api_key_scanner.py
            ;;
        2)
            print_step "启动Token健康监控..."
            if [[ -f "github_tokens.txt" ]]; then
                python token_health_monitor.py github_tokens.txt
            else
                print_error "github_tokens.txt文件不存在"
                return 1
            fi
            ;;
        3)
            print_step "后台启动服务..."
            nohup python app/api_key_scanner.py > scanner.log 2>&1 &
            echo $! > scanner.pid
            print_success "扫描器已在后台启动 (PID: $(cat scanner.pid))"
            
            if [[ -f "github_tokens.txt" ]]; then
                nohup python token_health_monitor.py github_tokens.txt --continuous > monitor.log 2>&1 &
                echo $! > monitor.pid
                print_success "监控器已在后台启动 (PID: $(cat monitor.pid))"
            fi
            
            echo ""
            print_info "查看日志："
            echo "  扫描器日志: tail -f scanner.log"
            echo "  监控器日志: tail -f monitor.log"
            echo ""
            print_info "停止服务："
            echo "  kill $(cat scanner.pid 2>/dev/null || echo 'PID')"
            echo "  kill $(cat monitor.pid 2>/dev/null || echo 'PID')"
            ;;
        4)
            echo ""
            print_info "运行命令："
            echo "  激活环境: source $VENV_PATH/bin/activate"
            echo "  运行扫描器: python app/api_key_scanner.py"
            echo "  运行监控: python token_health_monitor.py github_tokens.txt"
            echo "  退出环境: deactivate"
            ;;
        *)
            print_error "无效选择"
            return 1
            ;;
    esac
    
    return 0
}

# ============================================
# 环境检测和推荐
# ============================================
detect_available_modes() {
    local modes=()
    
    print_step "检测可用的部署模式..."
    echo ""
    
    # 检测Docker
    if check_docker_prerequisites 2>/dev/null; then
        modes+=("docker")
        print_success "Docker环境可用"
    else
        print_info "Docker环境不可用"
    fi
    
    # 检测本地Python
    if check_local_prerequisites 2>/dev/null; then
        modes+=("local")
        print_success "本地Python环境可用"
    else
        print_info "本地Python环境不可用"
    fi
    
    echo ""
    
    # 返回可用模式
    if [[ ${#modes[@]} -eq 0 ]]; then
        print_error "没有可用的部署环境"
        echo ""
        echo "请安装以下环境之一："
        echo "  - Docker和Docker Compose"
        echo "  - Python 3.8或更高版本"
        return 1
    elif [[ ${#modes[@]} -eq 1 ]]; then
        print_info "检测到唯一可用模式: ${modes[0]}"
        DEPLOYMENT_MODE="${modes[0]}"
        return 0
    else
        # 两种模式都可用，让用户选择
        return 0
    fi
}

# ============================================
# 主菜单
# ============================================
show_main_menu() {
    print_header "   🔍 API密钥扫描器 - 统一启动器 🔍"
    
    echo "欢迎使用API密钥扫描器统一启动器！"
    echo "本工具将帮助您选择合适的部署方式。"
    echo ""
    
    # 检测可用模式
    detect_available_modes
    
    # 如果已经确定了模式（只有一个可用）
    if [[ -n "$DEPLOYMENT_MODE" ]]; then
        echo ""
        read -p "是否使用${DEPLOYMENT_MODE}模式启动？(y/n): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "已取消"
            exit 0
        fi
    else
        # 显示选择菜单
        echo "请选择部署模式："
        echo ""
        echo "  ${BOLD}1)${NC} 🐳 Docker容器部署"
        echo "     ${CYAN}推荐：隔离性好，配置简单，包含WARP代理${NC}"
        echo ""
        echo "  ${BOLD}2)${NC} 💻 本地环境部署"
        echo "     ${CYAN}适合：开发调试，资源受限环境${NC}"
        echo ""
        echo "  ${BOLD}3)${NC} 📖 查看帮助文档"
        echo ""
        echo "  ${BOLD}4)${NC} 🔧 系统诊断"
        echo ""
        echo "  ${BOLD}5)${NC} 退出"
        echo ""
        
        read -p "请选择 [1-5]: " choice
        
        case $choice in
            1)
                DEPLOYMENT_MODE="docker"
                ;;
            2)
                DEPLOYMENT_MODE="local"
                ;;
            3)
                show_help
                return 0
                ;;
            4)
                run_diagnostics
                return 0
                ;;
            5)
                print_info "感谢使用，再见！"
                exit 0
                ;;
            *)
                print_error "无效的选择"
                return 1
                ;;
        esac
    fi
    
    # 执行选定的部署模式
    case $DEPLOYMENT_MODE in
        docker)
            deploy_with_docker
            ;;
        local)
            deploy_local
            ;;
        *)
            print_error "未知的部署模式"
            return 1
            ;;
    esac
    
    return $?
}

# ============================================
# 帮助文档
# ============================================
show_help() {
    print_header "帮助文档"
    
    echo "📚 部署模式说明："
    echo ""
    echo "1. Docker容器部署"
    echo "   - 优点：环境隔离、配置简单、包含代理"
    echo "   - 缺点：需要Docker环境、资源占用较高"
    echo "   - 适用：生产环境、VPS服务器"
    echo ""
    echo "2. 本地环境部署"
    echo "   - 优点：资源占用低、便于调试"
    echo "   - 缺点：需要配置Python环境、可能有依赖冲突"
    echo "   - 适用：开发环境、本地测试"
    echo ""
    echo "📝 配置文件说明："
    echo "   .env - 环境变量配置"
    echo "   queries.txt - 搜索查询配置"
    echo "   github_tokens.txt - GitHub Token列表（可选）"
    echo ""
    echo "🔗 相关文档："
    echo "   README.md - 项目说明"
    echo "   DOCKER_DEPLOY_GUIDE.md - Docker部署指南"
    echo "   DEPLOYMENT_GUIDE.md - 综合部署指南"
    echo ""
    
    read -p "按Enter键返回主菜单..."
    show_main_menu
}

# ============================================
# 系统诊断
# ============================================
run_diagnostics() {
    print_header "系统诊断"
    
    echo "🔍 正在进行系统诊断..."
    echo ""
    
    # 操作系统
    echo "操作系统: $(detect_os)"
    echo "主机名: $(hostname)"
    echo "当前用户: $(whoami)"
    echo "工作目录: $(pwd)"
    echo ""
    
    # Docker环境
    echo "Docker环境:"
    if command -v docker &> /dev/null; then
        echo "  Docker: $(docker --version 2>/dev/null || echo '未知版本')"
        if docker info &> /dev/null; then
            echo "  状态: 运行中"
        else
            echo "  状态: 未运行"
        fi
    else
        echo "  Docker: 未安装"
    fi
    
    if command -v docker-compose &> /dev/null; then
        echo "  Docker Compose: $(docker-compose --version 2>/dev/null || echo '未知版本')"
    else
        echo "  Docker Compose: 未安装"
    fi
    echo ""
    
    # Python环境
    echo "Python环境:"
    if command -v python3 &> /dev/null; then
        echo "  Python3: $(python3 --version 2>/dev/null || echo '未知版本')"
    fi
    if command -v python &> /dev/null; then
        echo "  Python: $(python --version 2>/dev/null || echo '未知版本')"
    fi
    if command -v pip &> /dev/null; then
        echo "  pip: $(pip --version 2>/dev/null | cut -d' ' -f2)"
    fi
    if command -v uv &> /dev/null; then
        echo "  UV: $(uv --version 2>/dev/null || echo '已安装')"
    fi
    echo ""
    
    # 配置文件
    echo "配置文件:"
    for file in .env queries.txt github_tokens.txt requirements.txt docker-compose.yml; do
        if [[ -f "$file" ]]; then
            echo "  ✓ $file ($(wc -l < "$file" 2>/dev/null || echo '0')行)"
        else
            echo "  ✗ $file"
        fi
    done
    echo ""
    
    # 数据目录
    echo "数据目录:"
    if [[ -d "data" ]]; then
        echo "  data/: 存在"
        echo "    - keys/: $(ls data/keys 2>/dev/null | wc -l || echo '0')个文件"
        echo "    - logs/: $(ls data/logs 2>/dev/null | wc -l || echo '0')个文件"
    else
        echo "  data/: 不存在"
    fi
    echo ""
    
    read -p "按Enter键返回主菜单..."
    show_main_menu
}

# ============================================
# 错误处理
# ============================================
handle_error() {
    local exit_code=$1
    local error_msg=$2
    
    print_error "$error_msg"
    log_to_file "ERROR: $error_msg (exit code: $exit_code)"
    
    echo ""
    echo "错误代码: $exit_code"
    echo "日志文件: $LOG_FILE"
    echo ""
    
    read -p "按Enter键退出..."
    exit $exit_code
}

# ============================================
# 信号处理
# ============================================
trap_handler() {
    echo ""
    print_warning "接收到中断信号"
    print_info "正在清理..."
    
    # 如果在虚拟环境中，退出
    if [[ -n "$VIRTUAL_ENV" ]]; then
        deactivate 2>/dev/null || true
    fi
    
    exit 130
}

trap trap_handler INT TERM

# ============================================
# 主程序入口
# ============================================
main() {
    # 初始化日志
    echo "" > "$LOG_FILE"
    log_to_file "统一启动器开始运行"
    log_to_file "操作系统: $(detect_os)"
    log_to_file "工作目录: $SCRIPT_DIR"
    
    # 切换到脚本所在目录
    cd "$SCRIPT_DIR"
    
    # 显示主菜单
    show_main_menu
    local result=$?
    
    # 处理结果
    if [[ $result -eq 0 ]]; then
        echo ""
        print_success "操作完成！"
        log_to_file "操作成功完成"
    else
        handle_error $result "操作失败"
    fi
    
    exit $result
}

# 运行主程序
main "$@"