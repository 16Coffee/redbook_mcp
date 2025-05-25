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
        # 执行缓存清理
        await _internal_cache_cleanup()
        
        # 清理浏览器资源
        await browser_manager.close()
        
        # 清理缓存管理器
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

# ===========================================
# 内部清理功能（不对外暴露为MCP工具）
# ===========================================

async def _internal_cache_cleanup():
    """内部缓存清理功能，用于程序启动时和定期维护"""
    try:
        # 清理过期缓存
        count = await cache_manager.cleanup_expired()
        logger.info(f"启动时清理了 {count} 个过期缓存")
        
        # 清理旧的日志文件
        import time
        log_dir = config.paths.logs_dir
        if log_dir.exists():
            current_time = time.time()
            for log_file in log_dir.glob("*.log"):
                if current_time - log_file.stat().st_mtime > 7 * 24 * 3600:  # 7天
                    log_file.unlink()
                    logger.info(f"清理旧日志文件: {log_file.name}")
        
        # 清理临时文件
        temp_patterns = ["*.tmp", "*.temp", "*~"]
        for pattern in temp_patterns:
            for temp_file in config.paths.base_dir.glob(f"**/{pattern}"):
                if temp_file.is_file():
                    temp_file.unlink()
                    logger.debug(f"清理临时文件: {temp_file}")
        
        logger.info("自动缓存清理完成")
    except Exception as e:
        logger.error(f"自动缓存清理失败: {e}")

def main():
    """主函数入口"""
    try:
        # 初始化并运行服务器
        logger.info("启动小红书MCP服务器...")
        
        # 启动前清理可能存在的浏览器进程和锁文件
        try:
            import os
            import shutil
            import psutil
            import subprocess
            import time
            
            logger.info("执行启动前清理...")
            
            # 1. 清理可能存在的浏览器进程
            killed_processes = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    cmdline_str = ' '.join(cmdline) if cmdline else ''
                    
                    # 匹配与当前项目相关的浏览器进程
                    if ('chromium' in proc.info['name'].lower() or 'chrome' in proc.info['name'].lower()) and 'redbook_mcp' in cmdline_str:
                        proc.terminate()
                        killed_processes += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            if killed_processes > 0:
                logger.info(f"已终止 {killed_processes} 个遗留的浏览器进程")
                # 等待进程完全终止
                time.sleep(1)
            
            # 2. 系统级清理命令
            if os.name == 'posix':  # macOS/Linux
                subprocess.run(['pkill', '-f', 'chromium.*redbook_mcp'], stderr=subprocess.PIPE)
            elif os.name == 'nt':   # Windows
                subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], stderr=subprocess.PIPE)
            
            # 3. 清理锁文件
            browser_data_dir = config.paths.browser_data_dir
            lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie"]
            for lock_file in lock_files:
                lock_path = os.path.join(browser_data_dir, lock_file)
                if os.path.exists(lock_path):
                    try:
                        if os.path.isfile(lock_path):
                            os.remove(lock_path)
                        elif os.path.isdir(lock_path):
                            shutil.rmtree(lock_path)
                        logger.info(f"清理了 {lock_file} 文件")
                    except Exception as e:
                        logger.warning(f"清理 {lock_file} 失败: {str(e)}")
            
            logger.info("启动前清理完成")
            
        except Exception as e:
            logger.warning(f"启动前清理失败，继续启动: {str(e)}")
        
        # 启动时执行自动清理
        try:
            asyncio.run(_internal_cache_cleanup())
        except Exception as e:
            logger.warning(f"启动清理失败，继续启动服务器: {e}")
        
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
