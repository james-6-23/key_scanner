#!/bin/bash

# ============================================
# API密钥扫描器 - Python虚拟环境快速搭建脚本
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

# 检查系统依赖
check_system_deps() {
    print_info "检查系统依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python未安装，请先安装Python 3.8或更高版本"
        exit 1
    fi
    
    # 检查Python版本
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null || python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null)
    if [[ $PYTHON_VERSION < "3.8" ]]; then
        print_error "Python版本过低，需要3.8或更高版本，当前版本: $PYTHON_VERSION"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        print_warning "pip未安装，将尝试安装..."
        # 尝试安装pip
        if command -v python3 &> /dev/null; then
            python3 -m ensurepip --upgrade
        else
            python -m ensurepip --upgrade
        fi
    fi
    
    print_success "系统依赖检查通过"
}

# 检查并安装UV
check_and_install_uv() {
    print_info "检查UV包管理器..."
    
    if command -v uv &> /dev/null; then
        print_success "UV已安装，版本: $(uv --version)"
        return
    fi
    
    print_warning "UV未安装，将尝试安装..."
    
    # 尝试使用curl安装
    if command -v curl &> /dev/null; then
        print_info "使用curl安装UV..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source "$HOME/.local/bin/uv" 2>/dev/null || true
    else
        print_warning "curl未安装，跳过UV安装"
        return
    fi
    
    if command -v uv &> /dev/null; then
        print_success "UV安装成功，版本: $(uv --version)"
    else
        print_warning "UV安装失败，将使用pip安装依赖"
    fi
}

# 创建虚拟环境
create_venv() {
    print_info "创建Python虚拟环境..."
    
    # 删除已存在的虚拟环境
    if [ -d ".venv" ]; then
        print_warning "虚拟环境已存在，删除重建..."
        rm -rf .venv
    fi
    
    # 创建虚拟环境
    if command -v python3 &> /dev/null; then
        python3 -m venv .venv
    else
        python -m venv .venv
    fi
    
    # 激活虚拟环境
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    else
        print_error "无法激活虚拟环境"
        exit 1
    fi
    
    print_success "虚拟环境创建成功并已激活"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."
    
    # 检查requirements.txt是否存在
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt文件不存在"
        exit 1
    fi
    
    # 如果UV可用，使用UV安装依赖
    if command -v uv &> /dev/null; then
        print_info "使用UV安装依赖（更快）..."
        uv pip install -r requirements.txt
    else
        # 使用pip安装依赖
        print_info "使用pip安装依赖..."
        pip install -r requirements.txt
    fi
    
    print_success "依赖安装完成"
}

# 显示使用说明
show_usage() {
    echo ""
    echo "============================================"
    echo "    Python环境搭建完成！"
    echo "============================================"
    echo ""
    echo "激活虚拟环境命令："
    if [ -f ".venv/bin/activate" ]; then
        echo "  source .venv/bin/activate"
    elif [ -f ".venv/Scripts/activate" ]; then
        echo "  source .venv/Scripts/activate"
    fi
    echo ""
    echo "退出虚拟环境命令："
    echo "  deactivate"
    echo ""
    echo "运行项目命令："
    echo "  python app/api_key_scanner.py"
    echo ""
    echo "运行Token健康监控："
    echo "  python token_health_monitor.py github_tokens.txt"
    echo ""
}

# 主函数
main() {
    echo "============================================"
    echo "    API密钥扫描器 - Python环境快速搭建"
    echo "============================================"
    echo ""
    
    # 执行检查和安装
    check_system_deps
    check_and_install_uv
    create_venv
    install_dependencies
    
    echo ""
    echo "============================================"
    print_success "Python环境搭建完成！"
    echo "============================================"
    echo ""
    
    show_usage
}

# 运行主函数
main