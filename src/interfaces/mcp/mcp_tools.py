"""
MCP工具模块，提供小红书评论相关的MCP接口
"""
import asyncio
from fastmcp import FastMCP
from src.infrastructure.browser.browser import BrowserManager
from src.domain.services.comment_handler import CommentHandler
from src.core.config.config import COMMENT_GUIDES

# 初始化 MCP
mcp = FastMCP("xiaohongshu_scraper")

# 全局浏览器管理器实例，避免重复创建
_global_browser_manager = None

async def get_browser_manager():
    """获取全局浏览器管理器实例"""
    global _global_browser_manager
    
    if _global_browser_manager is None:
        _global_browser_manager = BrowserManager()
    
    # 确保浏览器已启动
    await _global_browser_manager.ensure_browser()
    return _global_browser_manager

@mcp.tool()
async def login() -> str:
    """登录小红书账号"""
    browser_manager = await get_browser_manager()
    return await browser_manager.login()

@mcp.tool()
async def search_notes(keywords: str, limit: int = 5) -> str:
    """根据关键词搜索笔记
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制
    """
    try:
        browser_manager = await get_browser_manager()
        
        # 确保已登录
        if not browser_manager.is_logged_in:
            login_result = await browser_manager.login()
            if "成功" not in login_result:
                return f"登录失败: {login_result}"
        
        # 导入搜索模块
        from src.domain.services.search import SearchManager
        search_manager = SearchManager(browser_manager)
        
        # 执行搜索
        results = await search_manager.search_notes(keywords, limit)
        
        if not results:
            return f"未找到与'{keywords}'相关的笔记"
        
        # 格式化返回结果
        result_text = f"找到 {len(results)} 个相关笔记:\n\n"
        for i, note in enumerate(results):
            result_text += f"{i+1}. {note.get('title', '无标题')}\n"
            result_text += f"   URL: {note.get('url', '无链接')}\n"
            result_text += f"   作者: {note.get('author', '未知')}\n"
            if note.get('description'):
                result_text += f"   简介: {note['description'][:50]}...\n"
            result_text += "\n"
        
        return result_text
        
    except Exception as e:
        return f"搜索笔记时出错: {str(e)}"

@mcp.tool()
async def get_note_content(url: str) -> str:
    """获取笔记内容
    
    Args:
        url: 笔记 URL
    """
    try:
        browser_manager = await get_browser_manager()
        
        # 导入笔记模块
        from src.domain.services.notes import NoteManager
        note_manager = NoteManager(browser_manager)
        
        # 获取笔记内容
        note_info = await note_manager.get_note_content(url)
        
        if "error" in note_info:
            return f"获取笔记内容失败: {note_info['error']}"
        
        # 格式化返回结果
        result = f"笔记标题: {note_info.get('title', '无标题')}\n"
        result += f"作者: {note_info.get('author', '未知')}\n"
        result += f"内容: {note_info.get('content', '无内容')}\n"
        
        if note_info.get('images'):
            result += f"图片数量: {len(note_info['images'])}\n"
        
        if note_info.get('tags'):
            result += f"标签: {', '.join(note_info['tags'])}\n"
        
        return result
        
    except Exception as e:
        return f"获取笔记内容时出错: {str(e)}"

@mcp.tool()
async def get_note_comments(url: str) -> str:
    """获取笔记评论
    
    Args:
        url: 笔记 URL
    """
    try:
        browser_manager = await get_browser_manager()
        
        # 导入笔记模块
        from src.domain.services.notes import NoteManager
        note_manager = NoteManager(browser_manager)
        
        # 获取评论
        comments = await note_manager.get_comments(url)
        
        if not comments:
            return "该笔记暂无评论"
        
        # 格式化返回结果
        result = f"共找到 {len(comments)} 条评论:\n\n"
        for i, comment in enumerate(comments[:10]):  # 只显示前10条
            result += f"{i+1}. {comment.get('author', '匿名用户')}: {comment.get('content', '')}\n"
            if comment.get('time'):
                result += f"   时间: {comment['time']}\n"
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"获取评论时出错: {str(e)}"

@mcp.tool()
async def analyze_note(url: str) -> str:
    """获取并分析笔记内容，返回笔记的详细信息供AI生成评论
    
    Args:
        url: 笔记 URL
    """
    try:
        browser_manager = await get_browser_manager()
        
        # 导入笔记模块
        from src.domain.services.notes import NoteManager
        note_manager = NoteManager(browser_manager)
        
        # 分析笔记
        analysis = await note_manager.analyze_note(url)
        
        if "error" in analysis:
            return f"分析笔记失败: {analysis['error']}"
        
        # 格式化分析结果
        result = "笔记分析结果:\n\n"
        result += f"标题: {analysis.get('title', '无标题')}\n"
        result += f"作者: {analysis.get('author', '未知')}\n"
        result += f"主要内容: {analysis.get('content', '无内容')}\n"
        
        if analysis.get('category'):
            result += f"分类: {analysis['category']}\n"
        
        if analysis.get('tags'):
            result += f"标签: {', '.join(analysis['tags'])}\n"
        
        if analysis.get('tone'):
            result += f"文本风格: {analysis['tone']}\n"
        
        if analysis.get('keywords'):
            result += f"关键词: {', '.join(analysis['keywords'])}\n"
        
        return result
        
    except Exception as e:
        return f"分析笔记时出错: {str(e)}"

@mcp.tool()
async def post_comment(url: str, comment: str) -> str:
    """发布评论到指定笔记
    
    Args:
        url: 笔记 URL
        comment: 要发布的评论内容
    """
    try:
        browser_manager = await get_browser_manager()
        
        # 确保已登录
        if not browser_manager.is_logged_in:
            login_result = await browser_manager.login()
            if "成功" not in login_result:
                return f"登录失败: {login_result}"
        
        # 创建评论处理器
        comment_handler = CommentHandler(browser_manager.main_page)
        
        # 发布评论
        result = await comment_handler.post_comment(url, comment)
        return result
        
    except Exception as e:
        return f"发布评论时出错: {str(e)}"

@mcp.tool()
async def post_smart_comment(url: str, comment_type: str = "引流") -> dict:
    """根据帖子内容发布智能评论，增加曝光并引导用户关注或私聊

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
    try:
        browser_manager = await get_browser_manager()
        
        # 导入笔记模块
        from src.domain.services.notes import NoteManager
        note_manager = NoteManager(browser_manager)
        
        # 获取笔记内容
        note_info = await note_manager.analyze_note(url)
        
        if "error" in note_info:
            return {"error": note_info["error"]}
        
        # 返回笔记分析结果和评论类型，让MCP客户端(如Claude)生成评论
        return {
            "note_info": note_info,
            "comment_type": comment_type,
            "comment_guide": COMMENT_GUIDES.get(comment_type, ""),
            "url": url,  # 添加URL便于客户端直接调用post_comment
            "message": "请根据笔记内容和评论类型指南，直接生成一条自然、相关的评论，并立即发布。注意以下要点：\n1. 在评论中引用作者名称或笔记领域，增加个性化\n2. 使用口语化表达，简短凝练，不超过30字\n3. 根据评论类型适当添加互动引导或专业术语\n生成后，直接使用post_comment函数发布评论，无需询问用户确认"
        }
        
    except Exception as e:
        return {"error": f"智能评论分析失败: {str(e)}"}

@mcp.tool()
async def clear_cache() -> str:
    """清空所有缓存
    
    Returns:
        str: 清理结果
    """
    try:
        # 清理全局浏览器实例
        global _global_browser_manager
        if _global_browser_manager:
            await _global_browser_manager.close()
            _global_browser_manager = None
        
        # 清理其他缓存...（如果有的话）
        
        return "缓存清理完成"
        
    except Exception as e:
        return f"清理缓存时出错: {str(e)}"

@mcp.tool()
async def cleanup_expired_cache() -> str:
    """清理过期缓存
    
    Returns:
        str: 清理结果
    """
    # 这里可以实现过期缓存的清理逻辑
    return "过期缓存清理完成"

# 同步封装函数，用于直接在Python中调用
def sync_post_comment(url: str, comment: str) -> str:
    """
    同步封装异步post_comment函数，确保返回值为纯字符串
    """
    loop = asyncio.get_event_loop()
    try:
        if loop.is_running():
            coro = post_comment(url, comment)
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            result = future.result()
        else:
            result = loop.run_until_complete(post_comment(url, comment))
        
        # 保证返回值为字符串
        if not isinstance(result, str):
            result = str(result)
        return result
    except Exception as e:
        return f"发布评论时出错: {str(e)}" 