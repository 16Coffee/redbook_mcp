#!/bin/bash

# 小红书MCP服务部署脚本
# 作用：自动化部署小红书MCP服务

# 彩色输出
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 输出函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python环境
check_python() {
    log_info "检查Python环境..."
    
    # 检查Python
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        log_error "未找到Python。请先安装Python 3.8或更高版本: https://www.python.org/downloads/"
        exit 1
    fi
    
    # 检查Python版本
    PY_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo $PY_VERSION | cut -d. -f1)
    PY_MINOR=$(echo $PY_VERSION | cut -d. -f2)
    
    if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
        log_warn "Python版本 $PY_VERSION 低于推荐的3.8版本，可能导致兼容性问题"
        read -p "是否继续？(y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_info "Python版本 $PY_VERSION 符合要求"
    fi
}

# 创建虚拟环境
setup_virtual_env() {
    log_info "设置Python虚拟环境..."
    
    if [ -d ".venv" ]; then
        log_info "发现现有虚拟环境"
        read -p "是否重新创建虚拟环境？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "删除现有虚拟环境"
            rm -rf .venv
            $PYTHON_CMD -m venv .venv
            log_info "虚拟环境重新创建成功"
        else
            log_info "使用现有虚拟环境"
        fi
    else
        log_info "创建新的虚拟环境"
        $PYTHON_CMD -m venv .venv
        log_info "虚拟环境创建成功"
    fi
    
    # 激活虚拟环境
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi
    
    log_info "虚拟环境设置完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装Python依赖..."
    
    # 更新pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    
    log_info "依赖安装完成"
}

# 安装Playwright浏览器
install_playwright_browser() {
    log_info "安装Playwright浏览器..."
    
    playwright install chromium
    
    if [ $? -eq 0 ]; then
        log_info "Playwright浏览器安装成功"
    else
        log_warn "Playwright浏览器安装失败，这可能会影响后续使用"
        read -p "是否继续？(y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 创建数据目录
setup_data_dirs() {
    log_info "创建数据目录..."
    
    mkdir -p data browser_data
    chmod -R 755 data browser_data
    
    log_info "数据目录创建完成"
}

# 完成部署
finish_deployment() {
    log_info "部署完成！"
    
    cat << EOF

=====================================
    小红书MCP服务部署完成!
    
启动方法:
- 运行: ./run_xhs.sh

提示:
- 首次使用需要登录小红书账号
- 登录信息将存储在browser_data目录中
=====================================
EOF
    
    read -p "是否现在启动服务？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "启动服务..."
        chmod +x run_xhs.sh
        ./run_xhs.sh
    else
        log_info "您可以稍后手动启动服务: ./run_xhs.sh"
    fi
}

# 主函数
main() {
    echo -e "${GREEN}=====================================
    小红书MCP服务部署脚本
=====================================${NC}"
    
    # 执行部署步骤
    check_python
    setup_virtual_env
    install_dependencies
    install_playwright_browser
    setup_data_dirs
    finish_deployment
}

# 执行主函数
main 