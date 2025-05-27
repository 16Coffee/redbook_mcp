# 抖音 MCP 工具

🎵 为 CherryStudio 和其他 MCP 客户端提供抖音自动化功能的 MCP 服务器。

## ✨ 功能特性

- 🔐 **智能登录管理** - 自动保持登录状态，支持扫码登录和手机号登录
- 👤 **用户信息获取** - 获取当前登录用户的抖音信息
- 🔍 **视频搜索** - 根据关键词搜索抖音视频
- 📹 **视频信息获取** - 获取指定视频的详细信息
- 💾 **登录状态持久化** - 自动保存和恢复登录状态，30天内无需重复登录

## 🎯 核心优势

- **智能持久化登录**：首次登录后保存状态，30天内无需重复登录
- **多种登录方式**：支持扫码登录和手机号登录
- **稳定的浏览器管理**：自动处理浏览器异常和恢复
- **完整的错误处理**：提供清晰的错误信息和恢复建议

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows, macOS, Linux
- **浏览器**: Chrome/Chromium（自动下载）

## 🚀 安装和配置

### 1. 确保依赖已安装

```bash
# 在小红书 MCP 项目目录下
cd ~/redbook_mcp
pip install -r requirements.txt
```

### 2. 配置 CherryStudio

将以下配置添加到 CherryStudio 的 MCP 配置文件中：

```json
{
  "mcpServers": {
    "douyin_scraper": {
      "command": "python3",
      "args": ["-m", "src.interfaces.mcp.douyin_server"],
      "cwd": "/Users/yajun/Downloads/ai_project/redbook_mcp",
      "env": {
        "PYTHONPATH": "/Users/yajun/Downloads/ai_project/redbook_mcp"
      }
    }
  }
}
```

### 3. 重启 CherryStudio

重启 CherryStudio 即可使用抖音 MCP 工具。

## 📚 API 文档

### 可用工具

| 工具名称 | 描述 | 参数 |
|---------|------|------|
| `login_douyin` | 登录抖音 | 无 |
| `check_douyin_login_status` | 检查登录状态 | 无 |
| `clear_douyin_login` | 清除登录状态 | 无 |
| `get_douyin_user_info` | 获取用户信息 | 无 |
| `search_douyin_videos` | 搜索视频 | `keywords`, `limit` |
| `get_douyin_video_info` | 获取视频信息 | `url` |

### 使用示例

#### 1. 登录抖音
```
请帮我登录抖音
```

#### 2. 检查登录状态
```
检查我的抖音登录状态
```

#### 3. 获取用户信息
```
获取我的抖音用户信息
```

#### 4. 搜索视频
```
搜索抖音上关于"美食"的视频，显示前5个结果
```

#### 5. 获取视频信息
```
获取这个抖音视频的详细信息：https://www.douyin.com/video/xxxxx
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
