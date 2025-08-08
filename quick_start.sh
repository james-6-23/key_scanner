#!/bin/bash

# ============================================
# API密钥扫描器 - Docker快速部署脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 检查Docker和Docker Compose
check_docker() {
    print_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    print_success "Docker环境检查通过"
}

# 准备配置文件
prepare_config() {
    print_info "准备配置文件..."
    
    # 检查.env文件
    if [ ! -f ".env" ]; then
        if [ -f ".env.docker" ]; then
            print_info "复制.env.docker为.env..."
            cp .env.docker .env
            print_warning "请编辑.env文件，添加你的GitHub Token"
            print_warning "使用命令: nano .env 或 vim .env"
            read -p "按Enter键继续，或Ctrl+C退出进行配置..." 
        else
            print_error ".env文件不存在，请先创建配置文件"
            exit 1
        fi
    else
        print_success ".env文件已存在"
    fi
    
    # 检查queries.txt文件
    if [ ! -f "queries.txt" ]; then
        if [ -f "queries.example" ]; then
            print_info "复制queries.example为queries.txt..."
            cp queries.example queries.txt
            print_success "queries.txt文件已创建"
        else
            print_error "queries.txt文件不存在，请先创建查询文件"
            exit 1
        fi
    else
        print_success "queries.txt文件已存在"
    fi
}

# 验证GitHub Token
validate_token() {
    print_info "验证GitHub Token配置..."
    
    if grep -q "ghp_your_token_here" .env; then
        print_error "检测到示例Token，请先配置真实的GitHub Token"
        print_warning "编辑.env文件，将ghp_your_token_here替换为你的Token"
        exit 1
    fi
    
    print_success "GitHub Token配置检查通过"
}

# 构建和启动服务
start_services() {
    print_info "开始构建和启动服务..."
    
    # 拉取最新的WARP镜像
    print_info "拉取WARP代理镜像..."
    docker pull caomingjun/warp:latest
    
    # 构建主应用镜像
    print_info "构建主应用镜像..."
    docker-compose build --no-cache scanner
    
    # 启动所有服务
    print_info "启动所有服务..."
    docker-compose up -d
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        print_success "服务启动成功！"
    else
        print_error "服务启动失败，请检查日志"
        docker-compose logs --tail=50
        exit 1
    fi
}

# 显示服务状态
show_status() {
    print_info "服务状态："
    docker-compose ps
    
    echo ""
    print_info "查看日志命令："
    echo "  docker-compose logs -f          # 查看所有日志"
    echo "  docker-compose logs -f scanner  # 查看主应用日志"
    echo "  docker-compose logs -f warp     # 查看代理日志"
    
    echo ""
    print_info "停止服务命令："
    echo "  docker-compose down              # 停止所有服务"
    
    echo ""
    print_info "重启服务命令："
    echo "  docker-compose restart           # 重启所有服务"
}

# 主函数
main() {
    echo "============================================"
    echo "    API密钥扫描器 - Docker快速部署"
    echo "============================================"
    echo ""
    
    # 执行检查和部署
    check_docker
    prepare_config
    validate_token
    start_services
    
    echo ""
    echo "============================================"
    print_success "部署完成！"
    echo "============================================"
    echo ""
    
    show_status
}

# 运行主函数
main