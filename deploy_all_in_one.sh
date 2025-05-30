#!/bin/bash

# 小红书MCP服务一体化部署脚本
# 作用：自动化部署小红书MCP服务

# 彩色输出
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 默认配置
REPO_URL="https://github.com/16Coffee/redbook_mcp.git"
INSTALL_DIR="$HOME/Downloads/redbook_mcp"
AUTO_MODE=false

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

# 确认函数
confirm() {
    if [ "$AUTO_MODE" = true ]; then
        return 0
    fi
    
    local message=$1
    local default=${2:-n}
    
    if [ "$default" = "y" ]; then
        local prompt="Y/n"
        local default_value="y"
    else
        local prompt="y/N"
        local default_value="n"
    fi
    
    while true; do
        read -p "$(echo -e "${YELLOW}[确认]${NC} $message [$prompt]: ")" response
        response=${response:-$default_value}
        case $response in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "请输入 y 或 n.";;
        esac
    done
}

# 用户输入函数
get_input() {
    local prompt=$1
    local default=$2
    
    if [ "$AUTO_MODE" = true ]; then
        echo "$default"
        return
    fi
    
    read -p "$(echo -e "${YELLOW}[输入]${NC} $prompt (默认: $default): ")" input
    echo "${input:-$default}"
}

# 显示帮助信息
show_help() {
    cat << EOF
小红书MCP服务一体化部署脚本
=============================================

用法: $0 [选项]

选项:
  -y, --yes           自动模式，所有确认自动选择默认值
  -h, --help          显示此帮助信息
  -d, --dir <目录>    指定安装目录 (默认: ~/Downloads/redbook_mcp)

说明:
  此脚本会自动克隆小红书MCP项目并完成部署，
  包括创建虚拟环境、安装依赖和配置运行环境。

系统要求:
  - Git 客户端
  - Python 3.8+
  - 网络连接

示例:
  ./deploy_all_in_one.sh              # 交互式部署
  ./deploy_all_in_one.sh -y           # 自动部署（使用默认值）
  ./deploy_all_in_one.sh -d /opt/mcp  # 指定安装目录
EOF
    exit 0
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -y|--yes)
                AUTO_MODE=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            -d|--dir)
                if [[ -n "$2" && "$2" != -* ]]; then
                    INSTALL_DIR="$2"
                    shift 2
                else
                    log_error "缺少 --dir 参数值"
                    exit 1
                fi
                ;;
            *)
                log_error "未知参数: $1"
                echo "使用 --help 查看帮助信息"
                exit 1
                ;;
        esac
    done
}

# 检查并安装依赖
check_dependencies() {
    log_info "检查必要依赖..."
    
    # 检查Git
    if ! command -v git &>/dev/null; then
        log_error "未找到Git。请先安装Git: https://git-scm.com/downloads"
        exit 1
    fi
    
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
        if ! confirm "是否继续？" "n"; then
            exit 1
        fi
    else
        log_info "Python版本 $PY_VERSION 符合要求"
    fi
}

# 克隆或更新仓库
setup_repository() {
    log_info "准备代码库..."
    
    # 创建上级目录
    mkdir -p "$(dirname "$INSTALL_DIR")"
    
    # 检查目录是否存在
    if [ -d "$INSTALL_DIR" ]; then
        # 检查是否为Git仓库
        if [ -d "$INSTALL_DIR/.git" ]; then
            log_info "发现现有代码库，检查更新..."
            cd "$INSTALL_DIR"
            
            if confirm "是否更新代码库至最新版本？" "y"; then
                log_info "正在更新代码，请稍候..."
                git pull
                
                if [ $? -eq 0 ]; then
                    log_info "代码库更新成功"
                else
                    log_error "更新代码库失败"
                    if ! confirm "是否继续？" "n"; then
                        exit 1
                    fi
                fi
            fi
        else
            # 目录存在但不是Git仓库，将其初始化为Git仓库
            log_info "目录存在但不是Git仓库，正在初始化..."
            cd "$INSTALL_DIR"
            
            # 初始化仓库并添加远程源
            git init
            git remote add origin "$REPO_URL"
            
            # 获取最新代码并强制覆盖本地文件
            log_info "正在获取代码，请稍候..."
            git fetch origin
            
            if [ $? -ne 0 ]; then
                log_error "获取代码失败，可能是网络问题"
                if ! confirm "是否继续？" "n"; then
                    exit 1
                fi
            fi
            
            log_info "正在设置代码，请稍候..."
            git reset --hard origin/main 2>/dev/null || git reset --hard origin/master 2>/dev/null
            
            if [ $? -ne 0 ]; then
                log_warn "初始化代码库可能部分失败，将尝试继续..."
            else
                log_info "代码库初始化成功"
            fi
        fi
    else
        log_info "未发现代码库，准备克隆..."
        
        # 克隆仓库
        log_info "正在克隆代码库，这可能需要几分钟时间..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        
        if [ $? -eq 0 ]; then
            log_info "代码库克隆成功: $INSTALL_DIR"
        else
            log_error "克隆代码库失败，请检查网络连接或仓库URL"
            log_info "尝试使用简化命令直接克隆..."
            
            # 尝试使用带进度的克隆命令（适用于网络问题）
            git clone --progress "$REPO_URL" "$INSTALL_DIR"
            
            if [ $? -eq 0 ]; then
                log_info "代码库克隆成功: $INSTALL_DIR"
            else
                log_error "克隆代码库再次失败，建议手动克隆:"
                echo "git clone $REPO_URL $INSTALL_DIR"
                
                if [ -d "$INSTALL_DIR" ]; then
                    log_info "清理部分克隆的文件..."
                    rm -rf "$INSTALL_DIR"
                fi
                exit 1
            fi
        fi
    fi
}

# 创建虚拟环境
setup_virtual_env() {
    log_info "设置Python虚拟环境..."
    cd "$INSTALL_DIR"
    
    if [ -d ".venv" ]; then
        log_info "发现现有虚拟环境"
        if confirm "是否重新创建虚拟环境？" "n"; then
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
    
    # 创建默认的requirements.txt如果不存在
    if [ ! -f "requirements.txt" ]; then
        log_info "创建默认requirements.txt..."
        cat > requirements.txt << 'EOF'
playwright>=1.40.0
pytest-playwright>=0.4.0
pandas>=2.1.1
numpy>=1.26.4
asyncio==3.4.3
mcp>=1.9.0,<2.0.0
python-dotenv>=1.1.0
requests==2.31.0
schedule==1.2.0
tqdm==4.66.1
fastapi>=0.95.1
uvicorn>=0.22.0
psutil>=5.9.0
fastmcp>=2.5.1
EOF
        log_info "默认requirements.txt创建完成"
    fi
    
    log_info "虚拟环境设置完成"
}

# 安装依赖
install_dependencies() {
    log_info "安装Python依赖..."
    cd "$INSTALL_DIR"
    
    # 修复可能的SSL错误
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
        export PYTHONHTTPSVERIFY=0
    fi
    
    # 更新pip (忽略错误)
    pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org || true
    
    # 安装依赖 (忽略错误)
    pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org || {
        log_warn "安装部分依赖可能失败，但我们将继续"
    }
    
    # 确保关键依赖已安装
    pip install playwright fastmcp --trusted-host pypi.org --trusted-host files.pythonhosted.org
    
    log_info "依赖安装完成"
}

# 安装Playwright浏览器
install_playwright_browser() {
    log_info "安装Playwright浏览器..."
    cd "$INSTALL_DIR"
    
    playwright install chromium || {
        log_warn "Playwright浏览器安装可能失败，这可能会影响后续使用"
        if ! confirm "是否继续？" "y"; then
            exit 1
        fi
    }
    
    log_info "Playwright浏览器安装完成"
}

# 创建数据目录
setup_data_dirs() {
    log_info "创建数据目录..."
    cd "$INSTALL_DIR"
    
    mkdir -p data browser_data
    chmod -R 755 data browser_data
    
    log_info "数据目录创建完成"
}

# 创建启动脚本
create_start_script() {
    log_info "创建启动脚本..."
    cd "$INSTALL_DIR"
    
    # 检测可能的入口文件
    ENTRY_FILE=""
    ENTRY_ARGS=""
    
    if [ -f "main.py" ]; then
        ENTRY_FILE="main.py"
        ENTRY_ARGS="--stdio"
    elif [ -f "app.py" ]; then
        ENTRY_FILE="app.py"
    elif [ -f "server.py" ]; then
        ENTRY_FILE="server.py"
    elif [ -f "run.py" ]; then
        ENTRY_FILE="run.py"
    fi
    
    # 如果找不到入口文件，寻找任何Python文件作为可能的入口
    if [ -z "$ENTRY_FILE" ]; then
        # 查找包含"if __name__ == '__main__'"的Python文件
        MAIN_FILES=$(grep -l "__name__ == '__main__'" *.py 2>/dev/null)
        if [ -n "$MAIN_FILES" ]; then
            # 使用第一个找到的文件
            ENTRY_FILE=$(echo "$MAIN_FILES" | head -n 1)
            log_info "找到可能的入口文件: $ENTRY_FILE"
        else
            # 如果没有找到包含main的文件，使用任何Python文件
            PY_FILES=$(ls *.py 2>/dev/null | head -n 1)
            if [ -n "$PY_FILES" ]; then
                ENTRY_FILE=$(echo "$PY_FILES" | head -n 1)
                log_warn "未找到明确的入口文件，将使用: $ENTRY_FILE"
            else
                log_warn "未找到任何Python文件，将创建通用启动脚本"
                ENTRY_FILE="main.py"
                log_warn "请在运行前确认正确的启动命令"
            fi
        fi
    fi
    
    # 创建Unix启动脚本
    cat > run.sh << EOF
#!/bin/bash
# 小红书MCP服务启动脚本

cd "\$(dirname "\$0")"

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "错误: 未找到虚拟环境，请先运行部署脚本"
    exit 1
fi

# 启动服务
if [ -f "$ENTRY_FILE" ]; then
    echo "正在启动服务: python $ENTRY_FILE $ENTRY_ARGS"
    python $ENTRY_FILE $ENTRY_ARGS
else
    echo "错误: 未找到入口文件 $ENTRY_FILE"
    echo "请检查项目目录并手动启动正确的入口文件"
    echo "可用的Python文件:"
    ls *.py 2>/dev/null || echo "未找到Python文件"
    exit 1
fi
EOF
    chmod +x run.sh
    
    # 创建Windows启动脚本
    cat > run.bat << EOF
@echo off
:: 小红书MCP服务启动脚本

cd /d "%~dp0"

:: 激活虚拟环境
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo 错误: 未找到虚拟环境，请先运行部署脚本
    pause
    exit /b 1
)

:: 启动服务
if exist "$ENTRY_FILE" (
    echo 正在启动服务: python $ENTRY_FILE $ENTRY_ARGS
    python $ENTRY_FILE $ENTRY_ARGS
) else (
    echo 错误: 未找到入口文件 $ENTRY_FILE
    echo 请检查项目目录并手动启动正确的入口文件
    echo 可用的Python文件:
    dir /b *.py 2>nul || echo 未找到Python文件
    pause
    exit /b 1
)
pause
EOF
    
    log_info "启动脚本创建完成，将使用入口文件: $ENTRY_FILE"
}

# 完成部署
finish_deployment() {
    log_info "部署完成！"
    
    # 检查是否有入口文件
    cd "$INSTALL_DIR"
    
    # 列出目录文件供参考
    log_info "仓库中的文件列表:"
    ls -la | grep -v "^d" | head -n 10
    
    # 检查是否有Python文件
    PYTHON_FILES=$(ls *.py 2>/dev/null | wc -l)
    if [ "$PYTHON_FILES" -eq 0 ]; then
        log_warn "仓库中似乎没有Python文件，可能是仓库结构不符合预期"
        log_warn "请手动检查仓库内容并确定正确的启动方式"
    fi
    
    cat << EOF

=====================================
    小红书MCP服务部署完成!
    
安装目录: $INSTALL_DIR

启动方法:
- Linux/macOS: ./run.sh
- Windows: run.bat

提示:
- 首次使用需要登录小红书账号
- 登录信息将存储在browser_data目录中
=====================================
EOF
    
    if confirm "是否现在启动服务？" "n"; then
        log_info "启动服务..."
        cd "$INSTALL_DIR"
        
        # 检查入口文件是否存在
        if [ -f "run.sh" ]; then
            if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
                ./run.bat
            else
                ./run.sh
            fi
        else
            log_error "启动脚本不存在，请检查项目结构"
            
            # 尝试查找可能的入口文件
            log_info "尝试查找可能的入口文件..."
            POSSIBLE_ENTRIES=$(ls *.py 2>/dev/null)
            
            if [ -n "$POSSIBLE_ENTRIES" ]; then
                log_info "找到以下Python文件，可能是入口文件:"
                echo "$POSSIBLE_ENTRIES"
                
                if confirm "是否查看仓库文件结构？" "y"; then
                    find . -type f -name "*.py" | sort
                fi
            else
                log_error "未找到任何Python文件，请检查仓库结构"
            fi
        fi
    else
        log_info "您可以稍后手动启动服务"
    fi
}

# 主函数
main() {
    echo -e "${GREEN}=====================================
    小红书MCP服务一体化部署脚本
=====================================${NC}"
    
    parse_args "$@"
    
    if ! $AUTO_MODE; then
        # 防止用户误输入y/n作为目录
        while true; do
            INSTALL_DIR=$(get_input "请输入安装目录" "$INSTALL_DIR")
            
            # 验证输入不是单个字符的y或n（常见错误）
            if [[ "$INSTALL_DIR" == "y" || "$INSTALL_DIR" == "n" || "$INSTALL_DIR" == "Y" || "$INSTALL_DIR" == "N" ]]; then
                log_warn "输入似乎是确认回答(y/n)而非目录路径，请重新输入正确的安装路径"
                continue
            fi
            
            # 验证输入是合理的路径
            if [[ ! "$INSTALL_DIR" =~ ^/ && ! "$INSTALL_DIR" =~ ^~ && ! "$INSTALL_DIR" =~ ^[a-zA-Z]: ]]; then
                log_warn "输入的路径可能不是有效的绝对路径，推荐使用完整路径"
                if ! confirm "是否继续使用此路径？" "n"; then
                    continue
                fi
            fi
            
            break
        done
    fi
    
    log_info "安装目录: $INSTALL_DIR"
    
    if [ -d "$INSTALL_DIR" ] && [ "$AUTO_MODE" = false ]; then
        if ! confirm "安装目录已存在，可能覆盖现有文件，是否继续？" "y"; then
            log_info "部署已取消"
            exit 0
        fi
    fi
    
    # 执行部署步骤
    check_dependencies
    setup_repository
    setup_virtual_env
    install_dependencies
    install_playwright_browser
    setup_data_dirs
    create_start_script
    finish_deployment
}

# 执行主函数
main "$@" 