# 小红书 MCP 服务器

🔴 为 CherryStudio 和其他 MCP 客户端提供小红书自动化功能的 MCP 服务器。

## ✨ 功能特性

- 🔐 **智能登录管理** - 自动保持登录状态
- 💬 **评论发布** - 自动发布评论到指定笔记
- 🤖 **智能评论** - 基于内容生成相关评论
- 📄 **内容获取** - 获取笔记内容和评论
- 🔍 **笔记搜索** - 搜索相关笔记
- 📝 **内容发布** - 发布图文和视频笔记

## 🚀 快速开始

### 1. 安装

```bash
npm install -g xiaohongshu-mcp-server
```

### 2. 在 CherryStudio 中配置

打开 CherryStudio，进入设置 → MCP 服务器，添加新的服务器：

```json
{
  "name": "小红书",
  "command": "xiaohongshu-mcp",
  "args": []
}
```

### 3. 重启 CherryStudio

配置完成后重启 CherryStudio，即可在对话中使用小红书功能。

## 🛠️ 手动安装（开发者）

如果你想从源码安装或进行开发：

```bash
# 克隆仓库
git clone https://github.com/yourusername/xiaohongshu-mcp-server.git
cd xiaohongshu-mcp-server

# 安装依赖
pip install -r requirements.txt

# 启动服务器
python -m src.interfaces.mcp.server
```

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **Node.js**: 16.0 或更高版本（仅用于 npm 安装）
- **操作系统**: Windows, macOS, Linux
- **浏览器**: Chrome/Chromium（自动下载）

## 🎯 使用示例

安装配置完成后，你可以在 CherryStudio 中这样使用：

### 登录小红书
```
请帮我登录小红书
```

### 发布评论
```
请在这个小红书笔记下发布评论："内容很棒！"
笔记链接：https://www.xiaohongshu.com/explore/xxx
```

### 智能评论
```
请根据这个笔记内容生成一条引流评论：
https://www.xiaohongshu.com/explore/xxx
```

### 搜索笔记
```
请搜索关于"AI工具"的小红书笔记
```

## ⚙️ 高级配置

### 环境变量

你可以通过环境变量自定义配置：

```bash
# 浏览器数据目录
export XIAOHONGSHU_DATA_DIR="/path/to/browser/data"

# 日志级别
export XIAOHONGSHU_LOG_LEVEL="INFO"

# 超时设置
export XIAOHONGSHU_TIMEOUT="30000"
```

### CherryStudio 高级配置

```json
{
  "name": "小红书",
  "command": "xiaohongshu-mcp",
  "args": ["--dev"],
  "env": {
    "XIAOHONGSHU_LOG_LEVEL": "DEBUG"
  }
}
```

## 🔧 故障排除

### 常见问题

**Q: 安装后无法启动**
A: 确保已安装 Python 3.8+ 和所需依赖：
```bash
xiaohongshu-mcp --install-deps
```

**Q: 登录失败**
A: 检查网络连接，确保能正常访问小红书网站。

**Q: 评论发布失败**
A: 确保已登录且笔记 URL 包含完整的 xsec_token 参数。

### 调试模式

启用调试模式获取详细日志：

```json
{
  "name": "小红书",
  "command": "xiaohongshu-mcp",
  "args": ["--dev"]
}
```

## 📚 API 文档

### 可用工具

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `login_redbook` | 登录小红书 | 无 |
| `search_notes_redbook` | 搜索笔记 | `keywords`, `limit` |
| `get_note_content_redbook` | 获取笔记内容 | `url` |
| `get_note_comments_redbook` | 获取笔记评论 | `url` |
| `post_comment_redbook` | 发布评论 | `url`, `comment` |
| `post_smart_comment_redbook` | 智能评论 | `url`, `comment_type` |
| `analyze_note_redbook` | 分析笔记 | `url` |
| `publish_note_redbook` | 发布笔记 | `title`, `content`, `media_paths` |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [CherryStudio](https://github.com/kangfenmao/cherry-studio)
- [MCP 协议](https://github.com/modelcontextprotocol/specification)
- [项目仓库](https://github.com/yourusername/xiaohongshu-mcp-server)

## 📞 支持

如果遇到问题，请：

1. 查看 [故障排除](#故障排除) 部分
2. 搜索已有的 [Issues](https://github.com/yourusername/xiaohongshu-mcp-server/issues)
3. 创建新的 Issue 描述问题

---

⭐ 如果这个项目对你有帮助，请给个 Star！
