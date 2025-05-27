# 抖音 MCP 工具

🎵 为 CherryStudio 和其他 MCP 客户端提供抖音登录功能，集成在小红书 MCP 服务器中。

## ✨ 功能特性

- 🔐 **智能登录管理** - 自动保持登录状态，支持扫码登录和手机号登录
- 💾 **登录状态持久化** - 自动保存和恢复登录状态，30天内无需重复登录
- 🔄 **与小红书工具集成** - 在同一个 MCP 服务器中同时使用小红书和抖音功能

## 🎯 核心优势

- **智能持久化登录**：首次登录后保存状态，30天内无需重复登录
- **多种登录方式**：支持扫码登录和手机号登录
- **稳定的浏览器管理**：自动处理浏览器异常和恢复
- **完整的错误处理**：提供清晰的错误信息和恢复建议

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows, macOS, Linux
- **浏览器**: Chrome/Chromium（自动下载）

## 🚀 使用方法

### 1. 确保小红书 MCP 服务器已配置

抖音登录功能已集成到小红书 MCP 服务器中，无需单独配置。

### 2. 确认 CherryStudio 配置

确保您的 CherryStudio 已配置小红书 MCP 服务器：

```json
{
  "mcpServers": {
    "xiaohongshu_scraper": {
      "command": "python3",
      "args": ["-m", "src.interfaces.mcp.server"],
      "cwd": "/Users/yajun/Downloads/ai_project/redbook_mcp",
      "env": {
        "PYTHONPATH": "/Users/yajun/Downloads/ai_project/redbook_mcp"
      }
    }
  }
}
```

### 3. 重启 CherryStudio

重启 CherryStudio 即可同时使用小红书和抖音功能。

## 📚 API 文档

### 可用工具

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `login_douyin` | 登录抖音 | 无 |
| `login_redbook` | 登录小红书 | 无 |

**注意**：抖音工具目前只提供登录功能，其他功能（如用户信息获取、视频搜索等）暂未实现。

### 使用示例

#### 1. 登录抖音
```
请帮我登录抖音
```

#### 2. 登录小红书
```
请帮我登录小红书
```

#### 3. 同时使用两个平台
```
请先登录抖音，然后登录小红书
```

## 🔧 故障排除

### 常见问题

1. **登录失败**
   - 确保网络连接正常
   - 尝试清除登录状态后重新登录
   - 检查抖音是否有验证码或安全验证

2. **浏览器启动失败**
   - 确保系统有足够的内存
   - 检查是否有其他程序占用浏览器资源
   - 尝试重启 MCP 服务器

3. **搜索结果为空**
   - 确保已正确登录
   - 尝试使用不同的关键词
   - 检查网络连接

### 日志查看

```bash
# 查看详细日志
tail -f logs/app.log
```

## 🔒 数据安全

- 登录状态数据存储在本地，不会上传到任何服务器
- 支持手动清除登录状态
- 自动备份 cookies，防止数据丢失

## 📝 开发说明

### 项目结构

```
src/infrastructure/browser/
├── douyin_browser.py          # 抖音浏览器管理器
├── douyin_login_manager.py    # 抖音登录状态管理器
└── ...

src/interfaces/mcp/
├── douyin_server.py           # 抖音 MCP 服务器
├── douyin_tools.py            # 抖音 MCP 工具
└── ...
```

### 扩展功能

可以基于现有框架添加更多功能：
- 视频评论功能
- 视频点赞功能
- 关注用户功能
- 视频下载功能

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个工具！

## 📄 许可证

MIT License
