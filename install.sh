#!/bin/bash

# 小红书 MCP 服务器一键安装脚本
# 支持自动检测环境并选择最佳安装方式

set -e

echo "🔴 小红书 MCP 服务器安装程序"
echo "================================"

# 检测操作系统
OS="unknown"
case "$(uname -s)" in
    Darwin*)    OS="macos";;
    Linux*)     OS="linux";;
    CYGWIN*|MINGW*|MSYS*) OS="windows";;
esac

echo "📱 检测到操作系统: $OS"

# 检测 Node.js
check_nodejs() {
    if command -v node >/dev/null 2>&1; then
        NODE_VERSION=$(node --version | sed 's/v//')
        NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1)
        if [ "$NODE_MAJOR" -ge 16 ]; then
            echo "✅ 找到 Node.js $NODE_VERSION"
            return 0
        else
            echo "⚠️  Node.js 版本过低 ($NODE_VERSION)，需要 16+"
            return 1
        fi
    else
        echo "❌ 未找到 Node.js"
        return 1
    fi
}

# 检测 Python
check_python() {
    for cmd in python3 python; do
        if command -v $cmd >/dev/null 2>&1; then
            PYTHON_VERSION=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
            PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
            
            if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
                echo "✅ 找到 Python $PYTHON_VERSION ($cmd)"
                PYTHON_CMD=$cmd
                return 0
            fi
        fi
    done
    echo "❌ 未找到 Python 3.8+"
    return 1
}

# 安装 Node.js
install_nodejs() {
    echo "📦 正在安装 Node.js..."
    
    case $OS in
        "macos")
            if command -v brew >/dev/null 2>&1; then
                brew install node
            else
                echo "请安装 Homebrew 或从 https://nodejs.org/ 手动安装 Node.js"
                exit 1
            fi
            ;;
        "linux")
            if command -v apt >/dev/null 2>&1; then
                curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
                sudo apt-get install -y nodejs
            elif command -v yum >/dev/null 2>&1; then
                curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
                sudo yum install -y nodejs
            else
                echo "请从 https://nodejs.org/ 手动安装 Node.js"
                exit 1
            fi
            ;;
        *)
            echo "请从 https://nodejs.org/ 手动安装 Node.js"
            exit 1
            ;;
    esac
}

# 安装 Python
install_python() {
    echo "📦 正在安装 Python..."
    
    case $OS in
        "macos")
            if command -v brew >/dev/null 2>&1; then
                brew install python3
            else
                echo "请安装 Homebrew 或从 https://python.org/ 手动安装 Python"
                exit 1
            fi
            ;;
        "linux")
            if command -v apt >/dev/null 2>&1; then
                sudo apt update
                sudo apt install -y python3 python3-pip
            elif command -v yum >/dev/null 2>&1; then
                sudo yum install -y python3 python3-pip
            else
                echo "请手动安装 Python 3.8+"
                exit 1
            fi
            ;;
        *)
            echo "请从 https://python.org/ 手动安装 Python"
            exit 1
            ;;
    esac
}

# npm 安装方式
install_via_npm() {
    echo "🚀 使用 npm 安装..."
    npm install -g xiaohongshu-mcp-server
    echo "✅ 安装完成！"
    echo ""
    echo "📋 下一步：在 CherryStudio 中配置"
    echo '{'
    echo '  "name": "小红书",'
    echo '  "command": "xiaohongshu-mcp",'
    echo '  "args": []'
    echo '}'
}

# Python 安装方式
install_via_python() {
    echo "🚀 使用 Python 安装..."
    
    # 下载源码
    TEMP_DIR=$(mktemp -d)
    cd $TEMP_DIR
    
    echo "📥 下载源码..."
    if command -v git >/dev/null 2>&1; then
        git clone https://github.com/16Coffee/redbook_mcp.git
        cd redbook_mcp
    else
        curl -L https://github.com/16Coffee/redbook_mcp/archive/main.zip -o redbook_mcp.zip
        unzip redbook_mcp.zip
        cd redbook_mcp-main
    fi
    
    # 安装依赖
    echo "📦 安装依赖..."
    $PYTHON_CMD -m pip install -r requirements.txt
    
    # 创建全局命令
    INSTALL_DIR="$HOME/.xiaohongshu-mcp"
    mkdir -p $INSTALL_DIR
    cp -r . $INSTALL_DIR/
    
    # 创建启动脚本
    cat > $INSTALL_DIR/xiaohongshu-mcp << EOF
#!/bin/bash
cd $INSTALL_DIR
$PYTHON_CMD -m src.interfaces.mcp.server "\$@"
EOF
    chmod +x $INSTALL_DIR/xiaohongshu-mcp
    
    # 添加到 PATH
    if [[ ":$PATH:" != *":$HOME/.xiaohongshu-mcp:"* ]]; then
        echo 'export PATH="$HOME/.xiaohongshu-mcp:$PATH"' >> ~/.bashrc
        echo 'export PATH="$HOME/.xiaohongshu-mcp:$PATH"' >> ~/.zshrc
    fi
    
    echo "✅ 安装完成！"
    echo "🔄 请重新打开终端或运行: source ~/.bashrc"
    echo ""
    echo "📋 在 CherryStudio 中配置："
    echo '{'
    echo '  "name": "小红书",'
    echo '  "command": "'$INSTALL_DIR'/xiaohongshu-mcp",'
    echo '  "args": []'
    echo '}'
}

# 主安装流程
main() {
    echo "🔍 检查环境..."
    
    HAS_NODE=false
    HAS_PYTHON=false
    
    if check_nodejs; then
        HAS_NODE=true
    fi
    
    if check_python; then
        HAS_PYTHON=true
    fi
    
    # 选择安装方式
    if $HAS_NODE; then
        echo ""
        echo "🎯 推荐使用 npm 安装（最简单）"
        read -p "是否使用 npm 安装？(Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            install_via_npm
            return
        fi
    fi
    
    if $HAS_PYTHON; then
        echo ""
        echo "🐍 使用 Python 安装"
        install_via_python
        return
    fi
    
    # 都没有，询问用户想安装什么
    echo ""
    echo "❌ 缺少必要环境，请选择安装："
    echo "1) 安装 Node.js (推荐)"
    echo "2) 安装 Python"
    echo "3) 手动安装"
    read -p "请选择 (1-3): " choice
    
    case $choice in
        1)
            install_nodejs
            if check_nodejs; then
                install_via_npm
            fi
            ;;
        2)
            install_python
            if check_python; then
                install_via_python
            fi
            ;;
        3)
            echo ""
            echo "📖 手动安装指南："
            echo "1. 安装 Node.js 16+: https://nodejs.org/"
            echo "2. 安装 Python 3.8+: https://python.org/"
            echo "3. 重新运行此脚本"
            ;;
        *)
            echo "❌ 无效选择"
            exit 1
            ;;
    esac
}

# 运行主程序
main
