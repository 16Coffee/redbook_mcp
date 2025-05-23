"""
主模块，初始化MCP服务器并注册工具函数
"""
import asyncio
from fastmcp import FastMCP
from modules.browser import BrowserManager
from modules.notes import NoteManager
from modules.comments import CommentManager
from modules.publish import PublishManager

# 初始化 FastMCP 服务器
mcp = FastMCP("xiaohongshu_scraper")

# 初始化管理器实例
browser_manager = BrowserManager()
note_manager = NoteManager(browser_manager)
comment_manager = CommentManager(browser_manager, note_manager)
publish_manager = PublishManager(browser_manager)

@mcp.tool()
async def login():
    """登录小红书账号"""
    return await browser_manager.login()

@mcp.tool()
async def search_notes(keywords: str, limit: int = 5):
    """根据关键词搜索笔记
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制
    """
    return await note_manager.search_notes(keywords, limit)

@mcp.tool()
async def get_note_content(url: str):
    """获取笔记内容
    
    Args:
        url: 笔记 URL
    """
    return await note_manager.get_note_content(url)

@mcp.tool()
async def get_note_comments(url: str):
    """获取笔记评论
    
    Args:
        url: 笔记 URL
    """
    return await note_manager.get_note_comments(url)

@mcp.tool()
async def analyze_note(url: str):
    """获取并分析笔记内容，返回笔记的详细信息供AI生成评论
    
    Args:
        url: 笔记 URL
    """
    return await note_manager.analyze_note(url)

@mcp.tool()
async def post_comment(url: str, comment: str):
    """发布评论到指定笔记
    
    Args:
        url: 笔记 URL
        comment: 要发布的评论内容
    """
    return await comment_manager.post_comment(url, comment)

@mcp.tool()
async def post_smart_comment(url: str, comment_type: str = "引流"):
    """
    根据帖子内容发布智能评论，增加曝光并引导用户关注或私聊

    Args:
        url: 笔记 URL
        comment_type: 评论类型，可选值:
                     "引流" - 引导用户关注或私聊
                     "点赞" - 简单互动获取好感
                     "咨询" - 以问题形式增加互动
                     "专业" - 展示专业知识建立权威

    Returns:
        dict: 包含笔记信息和评论类型的字典，供MCP客户端(如Claude)生成评论
    """
    return await comment_manager.post_smart_comment(url, comment_type)

@mcp.tool()
async def publish_note(title: str, content: str, image_paths: list, topics: list = None):
    """发布小红书图文笔记
    
    Args:
        title: 笔记标题
        content: 笔记正文内容
        image_paths: 图片路径列表，支持本地路径
        topics: 话题标签列表（可选）
    
    Returns:
        str: 发布结果
    """
    return await publish_manager.publish_note(title, content, image_paths, topics)

if __name__ == "__main__":
    # 初始化并运行服务器
    print("启动小红书MCP服务器...")
    print("请在MCP客户端（如Claude for Desktop）中配置此服务器")
    mcp.run(transport='stdio')
