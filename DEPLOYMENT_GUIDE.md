# 小红书 MCP 服务器部署指南

本指南介绍如何将小红书 MCP 服务器部署为公共服务，让每个人都能在 CherryStudio 中使用。

## 🎯 部署方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **npm 包** | 安装简单，自动更新 | 需要本地 Python 环境 | 个人用户，开发者 |
| **Docker** | 环境隔离，跨平台 | 需要 Docker 知识 | 服务器部署，团队使用 |
| **源码分发** | 完全控制，可定制 | 安装复杂，维护困难 | 高级用户，定制需求 |

## 🚀 方案1: 发布 npm 包（推荐）

### 1.1 准备发布

```bash
# 1. 确保代码已提交
git add .
git commit -m "准备发布 npm 包"

# 2. 运行发布脚本
chmod +x scripts/publish.sh
./scripts/publish.sh
```

### 1.2 用户安装方式

用户只需要运行：

```bash
# 全局安装
npm install -g xiaohongshu-mcp-server

# 在 CherryStudio 中配置
{
  "name": "小红书",
  "command": "xiaohongshu-mcp",
  "args": []
}
```

### 1.3 自动更新

用户可以通过以下方式更新：

```bash
npm update -g xiaohongshu-mcp-server
```

## 🐳 方案2: Docker 部署

### 2.1 构建镜像

```bash
# 构建本地镜像
docker build -t xiaohongshu-mcp-server .

# 或使用 docker-compose
docker-compose build
```

### 2.2 发布到 Docker Hub

```bash
# 登录 Docker Hub
docker login

# 标记镜像
docker tag xiaohongshu-mcp-server yourusername/xiaohongshu-mcp-server:latest

# 推送镜像
docker push yourusername/xiaohongshu-mcp-server:latest
```

### 2.3 用户使用方式

```bash
# 拉取并运行
docker run -d \
  --name xiaohongshu-mcp \
  -p 8000:8000 \
  -v xiaohongshu_data:/app/data \
  yourusername/xiaohongshu-mcp-server:latest

# 在 CherryStudio 中配置
{
  "name": "小红书",
  "command": "docker",
  "args": ["exec", "xiaohongshu-mcp", "python", "-m", "src.interfaces.mcp.server"]
}
```

## 🌐 方案3: 云服务部署

### 3.1 部署到 Railway

1. 连接 GitHub 仓库到 Railway
2. 添加环境变量：
   ```
   XIAOHONGSHU_LOG_LEVEL=INFO
   PORT=8000
   ```
3. Railway 会自动部署

### 3.2 部署到 Heroku

```bash
# 安装 Heroku CLI
# 创建应用
heroku create xiaohongshu-mcp-server

# 设置 buildpack
heroku buildpacks:add heroku/python
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-google-chrome

# 部署
git push heroku main
```

### 3.3 部署到 Vercel

```bash
# 安装 Vercel CLI
npm i -g vercel

# 部署
vercel --prod
```

## 📦 方案4: GitHub Releases

### 4.1 创建发布包

```bash
# 创建发布脚本
cat > scripts/create_release.sh << 'EOF'
#!/bin/bash

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "用法: $0 <版本号>"
    exit 1
fi

# 创建发布目录
mkdir -p releases/xiaohongshu-mcp-$VERSION

# 复制必要文件
cp -r src/ releases/xiaohongshu-mcp-$VERSION/
cp requirements.txt releases/xiaohongshu-mcp-$VERSION/
cp README.md releases/xiaohongshu-mcp-$VERSION/
cp -r scripts/ releases/xiaohongshu-mcp-$VERSION/

# 创建安装脚本
cat > releases/xiaohongshu-mcp-$VERSION/install.sh << 'INSTALL_EOF'
#!/bin/bash
echo "🚀 安装小红书 MCP 服务器..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 请先安装 Python 3.8+"
    exit 1
fi

# 安装依赖
pip3 install -r requirements.txt

echo "✅ 安装完成！"
echo "启动命令: python3 -m src.interfaces.mcp.server"
INSTALL_EOF

chmod +x releases/xiaohongshu-mcp-$VERSION/install.sh

# 打包
cd releases
tar -czf xiaohongshu-mcp-$VERSION.tar.gz xiaohongshu-mcp-$VERSION/
zip -r xiaohongshu-mcp-$VERSION.zip xiaohongshu-mcp-$VERSION/

echo "✅ 发布包已创建:"
echo "  - xiaohongshu-mcp-$VERSION.tar.gz"
echo "  - xiaohongshu-mcp-$VERSION.zip"
EOF

chmod +x scripts/create_release.sh
```

### 4.2 用户安装方式

```bash
# 下载并解压
wget https://github.com/yourusername/xiaohongshu-mcp-server/releases/download/v1.0.0/xiaohongshu-mcp-1.0.0.tar.gz
tar -xzf xiaohongshu-mcp-1.0.0.tar.gz
cd xiaohongshu-mcp-1.0.0

# 安装
./install.sh

# 在 CherryStudio 中配置
{
  "name": "小红书",
  "command": "python3",
  "args": ["-m", "src.interfaces.mcp.server"],
  "cwd": "/path/to/xiaohongshu-mcp-1.0.0"
}
```

## 🔧 用户配置指南

### CherryStudio 配置示例

```json
{
  "mcpServers": {
    "xiaohongshu": {
      "command": "xiaohongshu-mcp",
      "args": [],
      "env": {
        "XIAOHONGSHU_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 高级配置

```json
{
  "mcpServers": {
    "xiaohongshu": {
      "command": "xiaohongshu-mcp",
      "args": ["--dev"],
      "env": {
        "XIAOHONGSHU_LOG_LEVEL": "DEBUG",
        "XIAOHONGSHU_DATA_DIR": "/custom/path/browser_data",
        "XIAOHONGSHU_TIMEOUT": "60000"
      },
      "timeout": 30000
    }
  }
}
```

## 📊 监控和维护

### 日志监控

```bash
# 查看日志
tail -f ~/.xiaohongshu-mcp/logs/server.log

# Docker 日志
docker logs xiaohongshu-mcp -f
```

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查 MCP 连接
xiaohongshu-mcp --test-connection
```

## 🚀 推荐部署流程

1. **开发阶段**: 使用源码直接运行
2. **测试阶段**: 使用 Docker 本地测试
3. **发布阶段**: 发布 npm 包
4. **企业部署**: 使用 Docker + 云服务

## 📞 用户支持

### 常见问题解决

1. **安装失败**: 检查 Python 版本和网络连接
2. **启动失败**: 查看日志文件，检查端口占用
3. **功能异常**: 确认登录状态，检查网络访问

### 获取帮助

- GitHub Issues: https://github.com/yourusername/xiaohongshu-mcp-server/issues
- 文档: https://github.com/yourusername/xiaohongshu-mcp-server/wiki
- 社区: https://discord.gg/your-discord

---

选择最适合你的部署方案，开始让更多人使用小红书 MCP 服务器吧！🎉
