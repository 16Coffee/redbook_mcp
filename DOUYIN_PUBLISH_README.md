# 抖音发布功能使用指南

🎬 为 CherryStudio 和其他 MCP 客户端提供抖音视频和图文发布功能。

## ✨ 功能特性

- 🎥 **视频发布** - 支持 MP4、MOV、AVI 等格式
- 📸 **图文发布** - 支持 JPG、PNG、GIF 等格式  
- 🤖 **智能检测** - 自动识别内容类型
- 🏷️ **话题标签** - 支持添加话题标签
- 🔒 **隐私设置** - 公开/私密/朋友可见
- 💬 **互动权限** - 评论/合拍/拼接权限设置

## 🚀 使用方法

### **基础用法**

```bash
# 发布视频（自动检测）
请帮我发布一个抖音视频，标题是"美食制作教程"，内容是"今天教大家做一道简单的家常菜"，视频文件路径是"/Users/username/video.mp4"

# 发布图文
请帮我发布抖音图文，标题是"今日穿搭分享"，内容是"简约风格的日常穿搭"，图片路径是["/Users/username/pic1.jpg", "/Users/username/pic2.jpg"]
```

### **高级用法**

```bash
# 完整参数发布
请使用 publish_douyin_content 工具发布内容，参数如下：
- title: "我的旅行日记"
- content: "分享这次旅行的美好回忆"
- media_paths: ["/Users/username/travel_video.mp4"]
- content_type: "video"
- topics: ["旅行", "美食", "风景"]
- privacy: "public"
- allow_comment: true
- allow_duet: true
- allow_stitch: false
```

## 📋 参数说明

### **必需参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `title` | string | 内容标题 |
| `content` | string | 内容描述 |
| `media_paths` | list | 媒体文件路径列表 |

### **可选参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `content_type` | string | "auto" | 内容类型："video", "image", "auto" |
| `topics` | list | null | 话题标签列表 |
| `privacy` | string | "public" | 隐私设置："public", "private", "friends" |
| `allow_comment` | bool | true | 是否允许评论 |
| `allow_duet` | bool | true | 是否允许合拍（仅视频） |
| `allow_stitch` | bool | true | 是否允许拼接（仅视频） |

## 📁 支持的文件格式

### **视频格式**
- MP4 (推荐)
- MOV
- AVI
- MKV
- FLV

### **图片格式**
- JPG/JPEG (推荐)
- PNG
- GIF
- WEBP

### **文件限制**
- 最大文件大小：500MB
- 视频时长：建议 15秒-3分钟
- 图片数量：最多 9 张

## 🎯 使用示例

### **示例 1：发布美食视频**

```bash
请帮我发布抖音视频：
- 标题：家常红烧肉制作教程
- 内容：简单易学的红烧肉做法，香甜软糯，老少皆宜
- 视频：/Users/chef/红烧肉教程.mp4
- 话题：美食、家常菜、教程
- 设置为公开，允许评论和合拍
```

### **示例 2：发布穿搭图文**

```bash
请发布抖音图文内容：
- 标题：秋日温柔穿搭分享
- 内容：温暖的秋日色调，简约而不失优雅
- 图片：["/Users/fashion/outfit1.jpg", "/Users/fashion/outfit2.jpg", "/Users/fashion/outfit3.jpg"]
- 话题：穿搭、秋装、时尚
- 仅朋友可见
```

### **示例 3：发布旅行 Vlog**

```bash
使用 publish_douyin_content 发布：
{
  "title": "云南大理三日游 Vlog",
  "content": "记录在大理的美好时光，古城漫步，洱海日落，每一刻都值得珍藏 #旅行 #大理 #vlog",
  "media_paths": ["/Users/traveler/大理vlog.mp4"],
  "content_type": "video",
  "topics": ["旅行", "大理", "vlog", "云南"],
  "privacy": "public",
  "allow_comment": true,
  "allow_duet": false,
  "allow_stitch": true
}
```

## ⚠️ 注意事项

### **发布前准备**
1. **确保已登录抖音账号**
   ```bash
   请帮我登录抖音
   ```

2. **检查文件路径**
   - 使用绝对路径
   - 确保文件存在且可访问
   - 检查文件格式和大小

3. **内容审核**
   - 确保内容符合抖音社区规范
   - 避免版权问题
   - 注意隐私保护

### **常见问题**

**Q: 发布失败怎么办？**
A: 检查登录状态、文件路径、网络连接，查看错误日志

**Q: 支持批量发布吗？**
A: 目前支持单次发布，可以多次调用工具实现批量发布

**Q: 可以定时发布吗？**
A: 当前版本不支持定时发布，发布后立即生效

**Q: 如何修改已发布的内容？**
A: 需要在抖音 App 或网页版中手动修改

## 🔧 故障排除

### **登录问题**
```bash
# 检查登录状态
请检查我的抖音登录状态

# 重新登录
请帮我重新登录抖音
```

### **文件问题**
- 检查文件路径是否正确
- 确认文件格式是否支持
- 验证文件大小是否超限

### **网络问题**
- 检查网络连接
- 尝试刷新页面
- 重启浏览器

## 📞 技术支持

如果遇到问题，可以：
1. 查看日志文件获取详细错误信息
2. 运行测试脚本检查功能状态
3. 检查抖音官方是否有系统维护

---

**现在您可以轻松地通过 CherryStudio 发布抖音内容了！** 🎉
