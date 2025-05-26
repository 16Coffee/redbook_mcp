#!/bin/bash

# 小红书 MCP 服务器发布脚本

set -e

echo "🚀 开始发布小红书 MCP 服务器..."

# 检查是否在正确的目录
if [ ! -f "package.json" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

# 检查是否已登录 npm
if ! npm whoami > /dev/null 2>&1; then
    echo "❌ 错误：请先登录 npm"
    echo "运行: npm login"
    exit 1
fi

# 检查 Git 状态
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  警告：有未提交的更改"
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 运行测试
echo "🧪 运行测试..."
if [ -f "test_optimized_comments.py" ]; then
    python test_optimized_comments.py || {
        echo "❌ 测试失败"
        exit 1
    }
fi

# 检查 Python 依赖
echo "📦 检查 Python 依赖..."
python -c "
import sys
required_modules = ['fastmcp', 'playwright', 'asyncio']
missing = []
for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        missing.append(module)
if missing:
    print(f'❌ 缺少依赖: {missing}')
    sys.exit(1)
print('✅ Python 依赖检查通过')
"

# 更新版本号
echo "📝 更新版本号..."
current_version=$(node -p "require('./package.json').version")
echo "当前版本: $current_version"

# 询问版本类型
echo "选择版本更新类型:"
echo "1) patch (修复版本)"
echo "2) minor (功能版本)"
echo "3) major (重大版本)"
echo "4) 自定义版本"
read -p "请选择 (1-4): " version_type

case $version_type in
    1)
        npm version patch
        ;;
    2)
        npm version minor
        ;;
    3)
        npm version major
        ;;
    4)
        read -p "请输入版本号 (例如: 1.2.3): " custom_version
        npm version $custom_version
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

new_version=$(node -p "require('./package.json').version")
echo "新版本: $new_version"

# 构建
echo "🔨 构建项目..."
chmod +x dist/index.js

# 创建 .npmignore
cat > .npmignore << EOF
# 开发文件
test_*.py
debug_*.py
*.pyc
__pycache__/
.pytest_cache/
.coverage

# Git 文件
.git/
.gitignore

# IDE 文件
.vscode/
.idea/
*.swp
*.swo

# 日志文件
*.log
logs/

# 临时文件
tmp/
temp/
.tmp/

# 浏览器数据
browser_data/
.deps_installed

# 环境文件
.env
.env.local

# 文档源文件
docs/
README_NPM.md

# 脚本
scripts/
EOF

# 预览将要发布的文件
echo "📋 预览发布文件..."
npm pack --dry-run

# 确认发布
read -p "确认发布版本 $new_version 到 npm？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 发布已取消"
    exit 1
fi

# 发布到 npm
echo "📤 发布到 npm..."
npm publish

# 推送到 Git
echo "📤 推送到 Git..."
git push origin main
git push origin --tags

# 创建 GitHub Release
if command -v gh &> /dev/null; then
    echo "🏷️  创建 GitHub Release..."
    gh release create "v$new_version" \
        --title "v$new_version" \
        --notes "发布版本 $new_version

## 安装方式

\`\`\`bash
npm install -g xiaohongshu-mcp-server
\`\`\`

## 在 CherryStudio 中配置

\`\`\`json
{
  \"name\": \"小红书\",
  \"command\": \"xiaohongshu-mcp\",
  \"args\": []
}
\`\`\`

查看完整文档：https://www.npmjs.com/package/xiaohongshu-mcp-server"
fi

echo "🎉 发布完成！"
echo ""
echo "📦 npm 包: https://www.npmjs.com/package/xiaohongshu-mcp-server"
echo "🏷️  版本: $new_version"
echo ""
echo "用户现在可以通过以下命令安装："
echo "npm install -g xiaohongshu-mcp-server"
echo ""
echo "然后在 CherryStudio 中配置："
echo '{
  "name": "小红书",
  "command": "xiaohongshu-mcp",
  "args": []
}'
