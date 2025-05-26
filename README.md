# 小红书 MCP 服务器

为 CherryStudio 提供小红书自动化功能的 MCP 服务器。

## 🚀 安装

### 方法1：一键安装（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/16Coffee/redbook_mcp/main/install.sh | bash
```

### 方法2：npm 安装

```bash
# 需要 Node.js 16+
npm install -g xiaohongshu-mcp-server
```

### 方法3：Python 安装

```bash
# 需要 Python 3.8+
git clone https://github.com/16Coffee/redbook_mcp.git
cd redbook_mcp
pip install -r requirements.txt
```

## ⚙️ 配置 CherryStudio

安装完成后，在 CherryStudio 中添加 MCP 服务器：

### npm 安装的配置：
```json
{
  "name": "小红书",
  "command": "xiaohongshu-mcp",
  "args": []
}
```

### Python 安装的配置：
```json
{
  "name": "小红书",
  "command": "python",
  "args": ["-m", "src.interfaces.mcp.server"],
  "cwd": "/path/to/redbook_mcp"
}
```

重启 CherryStudio 即可使用。

## 💬 使用方法

### 登录
```
请帮我登录小红书
```

### 搜索笔记
```
搜索关于"AI工具"的小红书笔记
```

### 发布评论
```
在这个笔记下发布评论："内容很棒！"
笔记链接：https://www.xiaohongshu.com/explore/xxx
```

### 智能评论
```
根据这个笔记内容生成一条引流评论
```

### 获取内容
```
获取这个笔记的详细内容：[笔记链接]
```

## 🔧 故障排除

**安装失败**：确保有 Node.js 16+ 或 Python 3.8+

**登录失败**：检查网络连接，重新扫码

**评论失败**：确保笔记链接完整且已登录

**调试模式**：
```bash
xiaohongshu-mcp --dev
```

## 📞 获取帮助

- [GitHub Issues](https://github.com/16Coffee/redbook_mcp/issues)
- [使用文档](https://github.com/16Coffee/redbook_mcp/wiki)

## ⚠️ 免责声明

仅供学习研究使用，请遵守小红书使用条款。
