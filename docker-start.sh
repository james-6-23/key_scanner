#!/bin/bash

# ============================================
# Docker快速启动脚本 - 超级版API密钥扫描器
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示标题
show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║         🚀 超级版API密钥扫描器 - Docker部署工具 🚀         ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查Docker环境
check_docker() {
    print_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装！请先安装Docker。"
        echo "访问 https://docs.docker.com/get-docker/ 获取安装指南"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装！请先安装Docker Compose。"
        echo "访问 https://docs.docker.com/compose/install/ 获取安装指南"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker服务未运行！请启动Docker服务。"
        exit 1
    fi
    
    print_success "Docker环境检查通过"
}

# 初始化配置文件
init_config() {
    print_info "初始化配置文件..."
    
    # 创建.env文件（如果不存在）
    if [ ! -f .env ]; then
        if [ -f env.example ]; then
            cp env.example .env
            print_success "已创建.env配置文件"
            print_warning "请编辑.env文件配置您的API密钥和其他设置"
        else
            print_warning "env.example不存在，创建默认.env文件"
            cat > .env << 'EOF'
# ========== 基础配置 ==========
DEFAULT_API_TYPE=gemini
SCAN_API_TYPES=gemini

# ========== 代理配置 ==========
PROXY=http://warp:1080

# ========== 凭证管理 ==========
USE_CREDENTIAL_MANAGER=true
CREDENTIAL_AUTO_HARVEST=false
CREDENTIAL_STORAGE_TYPE=redis

# ========== 负载均衡 ==========
LOAD_BALANCE_STRATEGY=adaptive

# ========== 监控配置 ==========
ENABLE_MONITORING=true
MONITORING_INTERVAL=300

# ========== 性能优化 ==========
HAJIMI_MAX_WORKERS=10
HAJIMI_BATCH_SIZE=10
HAJIMI_BATCH_INTERVAL=60
EOF
            print_success "已创建默认.env文件"
        fi
    else
        print_info ".env文件已存在"
    fi
    
    # 创建queries.txt文件（如果不存在）
    if [ ! -f queries.txt ]; then
        if [ -f queries.example ]; then
            cp queries.example queries.txt
            print_success "已创建queries.txt文件"
        else
            echo "test query" > queries.txt
            print_warning "已创建默认queries.txt文件，请添加您的查询"
        fi
    else
        print_info "queries.txt文件已存在"
    fi
    
    # 创建github_tokens.txt文件（如果不存在）
    if [ ! -f github_tokens.txt ]; then
        touch github_tokens.txt
        print_info "已创建空的github_tokens.txt文件"
    fi
    
    # 创建必要的目录
    mkdir -p logs monitoring config/queries
    print_success "目录结构创建完成"
}

# 构建镜像
build_images() {
    print_info "构建Docker镜像..."
    docker-compose build --no-cache
    print_success "镜像构建完成"
}

# 启动服务
start_services() {
    print_info "启动服务..."
    docker-compose up -d
    print_success "服务启动完成"
    
    # 等待服务就绪
    print_info "等待服务就绪..."
    sleep 5
    
    # 检查服务状态
    docker-compose ps
}

# 显示服务信息
show_info() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}服务已成功启动！${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}📊 服务状态:${NC}"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo -e "${CYAN}🔧 管理命令:${NC}"
    echo "  查看日志:     docker-compose logs -f scanner"
    echo "  进入启动器:   docker-compose exec scanner python scanner_launcher.py"
    echo "  快速扫描:     docker-compose exec scanner python app/api_key_scanner_super.py"
    echo "  停止服务:     docker-compose down"
    echo "  重启服务:     docker-compose restart"
    echo ""
    echo -e "${CYAN}🌐 Web界面:${NC}"
    echo "  监控面板:     http://localhost:8080"
    echo ""
    echo -e "${CYAN}📁 数据位置:${NC}"
    echo "  扫描结果:     ./logs/"
    echo "  监控数据:     ./monitoring/"
    echo ""
}

# 停止服务
stop_services() {
    print_info "停止服务..."
    docker-compose down
    print_success "服务已停止"
}

# 清理数据
clean_data() {
    print_warning "清理所有数据..."
    read -p "确定要清理所有数据吗？这将删除所有扫描结果和缓存！(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        rm -rf logs/* monitoring/*
        print_success "数据清理完成"
    else
        print_info "取消清理操作"
    fi
}

# 更新系统
update_system() {
    print_info "更新系统..."
    git pull origin main
    docker-compose build --no-cache
    docker-compose up -d
    print_success "系统更新完成"
}

# 交互式菜单
show_menu() {
    echo ""
    echo -e "${PURPLE}请选择操作:${NC}"
    echo "  1) 🚀 快速启动（推荐）"
    echo "  2) 🔨 重新构建并启动"
    echo "  3) 📊 查看服务状态"
    echo "  4) 📝 查看日志"
    echo "  5) 🎮 进入交互式启动器"
    echo "  6) ⚡ 执行快速扫描"
    echo "  7) 🛑 停止服务"
    echo "  8) 🧹 清理数据"
    echo "  9) 🔄 更新系统"
    echo "  0) 退出"
    echo ""
    read -p "请输入选项 [0-9]: " choice
    
    case $choice in
        1)
            init_config
            start_services
            show_info
            ;;
        2)
            init_config
            build_images
            start_services
            show_info
            ;;
        3)
            docker-compose ps
            ;;
        4)
            docker-compose logs -f --tail=100
            ;;
        5)
            docker-compose exec scanner python scanner_launcher.py
            ;;
        6)
            docker-compose exec scanner python app/api_key_scanner_super.py
            ;;
        7)
            stop_services
            ;;
        8)
            clean_data
            ;;
        9)
            update_system
            ;;
        0)
            print_info "退出"
            exit 0
            ;;
        *)
            print_error "无效选项"
            ;;
    esac
}

# 主函数
main() {
    show_banner
    check_docker
    
    # 如果提供了参数，执行对应操作
    case "${1:-}" in
        start)
            init_config
            start_services
            show_info
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            start_services
            show_info
            ;;
        build)
            build_images
            ;;
        logs)
            docker-compose logs -f --tail=100
            ;;
        status)
            docker-compose ps
            ;;
        clean)
            clean_data
            ;;
        update)
            update_system
            ;;
        launcher)
            docker-compose exec scanner python scanner_launcher.py
            ;;
        scan)
            shift
            docker-compose exec scanner python app/api_key_scanner_super.py "$@"
            ;;
        help|--help|-h)
            echo "使用方法: $0 [命令]"
            echo ""
            echo "命令:"
            echo "  start     - 启动服务"
            echo "  stop      - 停止服务"
            echo "  restart   - 重启服务"
            echo "  build     - 构建镜像"
            echo "  logs      - 查看日志"
            echo "  status    - 查看状态"
            echo "  clean     - 清理数据"
            echo "  update    - 更新系统"
            echo "  launcher  - 进入启动器"
            echo "  scan      - 执行扫描"
            echo "  help      - 显示帮助"
            echo ""
            echo "不带参数运行将显示交互式菜单"
            ;;
        "")
            # 无参数，显示交互式菜单
            while true; do
                show_menu
            done
            ;;
        *)
            print_error "未知命令: $1"
            echo "使用 '$0 help' 查看帮助"
            exit 1
            ;;
    esac
}

# 捕获Ctrl+C
trap 'echo ""; print_warning "用户中断"; exit 1' INT

# 运行主函数
main "$@"