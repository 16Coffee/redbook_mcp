# 小红书 MCP 服务器

🔴 为 CherryStudio 和其他 MCP 客户端提供小红书自动化功能的 MCP 服务器。

## ✨ 功能特性

- 🔐 **智能登录管理** - 自动保持登录状态，支持扫码登录
- 💬 **评论发布** - 自动发布评论到指定笔记
- 🤖 **智能评论** - 基于笔记内容生成相关评论
- 📄 **内容获取** - 获取笔记内容和评论信息
- 🔍 **笔记搜索** - 根据关键词搜索相关笔记
- 📝 **内容发布** - 发布图文和视频笔记
- 📊 **内容分析** - 分析笔记内容，提取关键信息

## 🎯 核心优势

- **深度集成AI能力**：利用 MCP 客户端的大模型能力，生成更自然、相关的评论内容
- **智能持久化登录**：首次登录后保存状态，30天内无需重复登录
- **多维度内容获取**：集成多种获取方法，确保能完整获取各类笔记信息
- **两步式评论流程**：先分析笔记内容，然后由 AI 生成并发布评论

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **Node.js**: 16.0 或更高版本（仅用于 npm 安装）
- **操作系统**: Windows, macOS, Linux
- **浏览器**: Chrome/Chromium（自动下载）

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

### 方法3：Python 源码安装

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

### 高级配置

```json
{
  "name": "小红书",
  "command": "xiaohongshu-mcp",
  "args": ["--dev"],
  "env": {
    "XIAOHONGSHU_LOG_LEVEL": "DEBUG",
    "XIAOHONGSHU_DATA_DIR": "/custom/path/browser_data"
  }
}
```

重启 CherryStudio 即可使用。

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

### 智能评论类型

| 类型 | 描述 | 适用场景 |
|------|------|----------|
| **引流** | 引导用户关注或私聊 | 增加粉丝或私信互动 |
| **点赞** | 简单互动获取好感 | 增加曝光和互动率 |
| **咨询** | 以问题形式增加互动 | 引发博主回复，增加互动深度 |
| **专业** | 展示专业知识建立权威 | 建立专业形象，增强可信度 |

## 🔧 故障排除

### 常见问题

**安装失败**：确保有 Node.js 16+ 或 Python 3.8+

**权限错误**：使用 `sudo npm install -g xiaohongshu-mcp-server` 或配置用户级 npm

**登录失败**：检查网络连接，重新扫码

**评论失败**：确保笔记链接完整且已登录

**依赖问题**：
```bash
# npm 方式
sudo pip3 install fastmcp playwright

# 源码方式
pip install -r requirements.txt
```

### 调试模式

```bash
xiaohongshu-mcp --dev
```

或在 CherryStudio 配置中添加：
```json
{
  "args": ["--dev"]
}
```

## 📞 获取帮助

- [GitHub Issues](https://github.com/16Coffee/redbook_mcp/issues)
- [使用文档](https://github.com/16Coffee/redbook_mcp/wiki)
- [MCP 协议](https://github.com/modelcontextprotocol/specification)
- [CherryStudio](https://github.com/kangfenmao/cherry-studio)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

## 📖 使用教程

### 🔐 登录小红书

```
请帮我登录小红书
```

首次使用时会打开浏览器窗口，扫码登录。登录成功后，状态会自动保存，30天内无需重复登录。

### 🔍 搜索笔记

```
搜索关于"AI工具"的小红书笔记
```

```
帮我搜索小红书笔记，关键词为旅游，返回10条结果
```

根据关键词搜索小红书笔记，可指定返回结果数量（默认5条）。

### 📄 获取笔记内容

```
获取这个笔记的详细内容：https://www.xiaohongshu.com/explore/xxx
```

```
请查看这个小红书笔记的内容：[笔记链接]
```

获取指定笔记的标题、作者、发布时间和正文内容。

### 💬 发布评论

```
在这个笔记下发布评论："内容很棒！"
笔记链接：https://www.xiaohongshu.com/explore/xxx
```

```
帮我发布这条评论到笔记：[笔记链接]
评论内容：这个分享太实用了！
```

将指定的评论内容发布到笔记页面。

### 🤖 智能评论

```
根据这个笔记内容生成一条引流评论：
https://www.xiaohongshu.com/explore/xxx
```

```
帮我为这个笔记写一条专业类型的评论：[笔记链接]
```

基于笔记内容自动生成相关评论，支持四种类型：
- **引流型**：引导关注或私聊
- **点赞型**：简单互动获取好感
- **咨询型**：以问题形式增加互动
- **专业型**：展示专业知识建立权威

### 📊 分析笔记

```
帮我分析这篇小红书笔记：https://www.xiaohongshu.com/explore/xxx
```

分析笔记内容，提取关键信息和所属领域。

### 💭 获取评论

```
帮我获取这篇笔记的评论：https://www.xiaohongshu.com/explore/xxx
```

获取指定笔记下的评论内容，包括评论者、评论文本和时间信息。

### 📝 发布笔记

```
帮我发布一篇小红书笔记，标题是"健康早餐分享"，内容是"今天分享我的减脂早餐，高蛋白低脂肪，营养又美味！"，使用图片"./images/breakfast.jpg"，添加话题"减脂餐"和"健康饮食"
```

发布图文笔记到小红书平台，支持：
- 上传多张图片
- 添加话题标签
- 自动处理发布流程

### 💡 使用技巧

1. **笔记链接格式**：确保使用完整的笔记链接，包含 `xsec_token` 参数
2. **评论频率控制**：建议每天发布评论不超过30条，避免账号风险
3. **内容质量**：智能评论会根据笔记内容生成相关性高的评论
4. **登录状态**：如果功能异常，可以重新登录小红书

### 🔄 工作流程示例

```
用户: 帮我为这个小红书笔记写一条专业类型的评论：https://www.xiaohongshu.com/explore/xxxx

AI: 我会帮您写一条专业类型的评论。让我先获取笔记内容并分析。

[调用 analyze_note 工具获取笔记信息]

AI: 我已经分析了这篇关于护肤的笔记。基于内容，我生成了以下专业评论：

"从成分角度来看，烟酰胺确实对改善肌肤屏障很有效果，建议配合神经酰胺使用，效果会更好。感谢分享这么详细的护肤心得！"

[调用 post_comment 工具发布评论]

AI: 评论已成功发布！
```

## ⚠️ 免责声明

本工具仅供学习和研究使用，请遵守小红书使用条款和相关法律法规。使用过程中请注意：

- 遵守平台规则，避免过度操作
- 控制评论发布频率，防止账号风险
- 尊重原创内容，发布有价值的评论
- 不用于恶意营销或垃圾信息传播
