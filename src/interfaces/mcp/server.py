"""
主模块，初始化MCP服务器并注册工具函数
"""
import asyncio
from fastmcp import FastMCP
from src.infrastructure.browser.browser import BrowserManager
from src.domain.services.notes import NoteManager
from src.domain.services.comments import CommentManager
from src.domain.services.publish import PublishManager
from src.core.config.config import config
from src.core.logging.logger import logger
from src.infrastructure.cache.cache import cache_manager
from src.core.exceptions.exceptions import RedBookMCPException

# 验证配置
try:
    config.validate()
    logger.info("配置验证成功")
except Exception as e:
    logger.error(f"配置验证失败: {str(e)}")
    raise e

# 初始化 FastMCP 服务器
mcp = FastMCP("xiaohongshu_scraper")

# 初始化管理器实例
browser_manager = BrowserManager()
note_manager = NoteManager(browser_manager)
comment_manager = CommentManager(browser_manager, note_manager)
publish_manager = PublishManager(browser_manager)

async def cleanup_resources():
    """清理资源"""
    try:
        await browser_manager.close()
        await cache_manager.cleanup_expired()
        logger.info("资源清理完成")
    except Exception as e:
        logger.error(f"资源清理失败: {str(e)}")

@mcp.tool()
async def login():
    """登录小红书账号"""
    try:
        result = await browser_manager.login()
        logger.info(f"登录操作完成: {result}")
        return result
    except Exception as e:
        error_msg = f"登录失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def search_notes(keywords: str, limit: int = 5):
    """根据关键词搜索笔记
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制
    """
    try:
        # 检查缓存
        cache_key = f"search_notes:{keywords}:{limit}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"从缓存获取搜索结果: {keywords}")
            return cached_result
        
        result = await note_manager.search_notes(keywords, limit)
        
        # 缓存结果（10分钟）
        await cache_manager.set(cache_key, result, ttl=600)
        
        logger.info(f"搜索笔记完成: {keywords}, 返回 {limit} 条结果")
        return result
    except Exception as e:
        error_msg = f"搜索笔记失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_note_content(url: str):
    """获取笔记内容
    
    Args:
        url: 笔记 URL
    """
    try:
        # 检查缓存
        cache_key = f"note_content:{url}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"从缓存获取笔记内容: {url}")
            return cached_result
        
        result = await note_manager.get_note_content(url)
        
        # 缓存结果（30分钟）
        await cache_manager.set(cache_key, result, ttl=1800)
        
        logger.info(f"获取笔记内容完成: {url}")
        return result
    except Exception as e:
        error_msg = f"获取笔记内容失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_note_comments(url: str):
    """获取笔记评论
    
    Args:
        url: 笔记 URL
    """
    try:
        result = await note_manager.get_note_comments(url)
        logger.info(f"获取笔记评论完成: {url}")
        return result
    except Exception as e:
        error_msg = f"获取笔记评论失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def analyze_note(url: str):
    """获取并分析笔记内容，返回笔记的详细信息供AI生成评论
    
    Args:
        url: 笔记 URL
    """
    try:
        result = await note_manager.analyze_note(url)
        logger.info(f"分析笔记完成: {url}")
        return result
    except Exception as e:
        error_msg = f"分析笔记失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def post_comment(url: str, comment: str):
    """发布评论到指定笔记
    
    Args:
        url: 笔记 URL
        comment: 要发布的评论内容
    """
    try:
        result = await comment_manager.post_comment(url, comment)
        logger.info(f"发布评论完成: {url}")
        return result
    except Exception as e:
        error_msg = f"发布评论失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

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
    try:
        result = await comment_manager.post_smart_comment(url, comment_type)
        logger.info(f"智能评论分析完成: {url}, 类型: {comment_type}")
        return result
    except Exception as e:
        error_msg = f"智能评论分析失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def publish_note(title: str, content: str, media_paths: list, topics: list = None):
    """发布小红书图文或视频笔记
    
    Args:
        title: 笔记标题
        content: 笔记正文内容
        media_paths: 媒体文件路径列表，支持本地图片和视频路径
        topics: 话题标签列表（可选）
    
    Returns:
        str: 发布结果
    """
    try:
        result = await publish_manager.publish_note(title, content, media_paths, topics)
        logger.info(f"发布笔记完成: {title}")
        return result
    except Exception as e:
        error_msg = f"发布笔记失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def clear_cache():
    """清空所有缓存
    
    Returns:
        str: 清理结果
    """
    try:
        await cache_manager.clear()
        logger.info("手动清空缓存完成")
        return "缓存已清空"
    except Exception as e:
        error_msg = f"清空缓存失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def cleanup_expired_cache():
    """清理过期缓存
    
    Returns:
        str: 清理结果
    """
    try:
        count = await cache_manager.cleanup_expired()
        result = f"已清理 {count} 个过期缓存"
        logger.info(result)
        return result
    except Exception as e:
        error_msg = f"清理过期缓存失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def main():
    """主函数入口"""
    try:
        # 初始化并运行服务器
        logger.info("启动小红书MCP服务器...")
        logger.info("请在MCP客户端（如Claude for Desktop）中配置此服务器")
        
        # 注册清理函数
        import atexit
        atexit.register(lambda: asyncio.run(cleanup_resources()))
        
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在清理资源...")
        asyncio.run(cleanup_resources())
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
