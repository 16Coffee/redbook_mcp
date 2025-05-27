"""
抖音 MCP 服务器主模块
"""
import asyncio
from fastmcp import FastMCP
from src.infrastructure.browser.douyin_browser import DouyinBrowserManager
from src.core.config.config import config
from src.core.logging.logger import logger

# 验证配置
try:
    config.validate()
    logger.info("抖音 MCP 配置验证成功")
except Exception as e:
    logger.error(f"抖音 MCP 配置验证失败: {str(e)}")
    raise e

# 初始化 FastMCP 服务器
mcp = FastMCP("douyin_scraper")

# 初始化管理器实例
douyin_browser_manager = DouyinBrowserManager()

async def cleanup_resources():
    """清理资源"""
    try:
        # 清理浏览器资源
        await douyin_browser_manager.close_browser()
        logger.info("抖音 MCP 资源清理完成")
    except Exception as e:
        logger.error(f"抖音 MCP 资源清理失败: {str(e)}")

@mcp.tool()
async def login_douyin():
    """登录抖音账号"""
    try:
        result = await douyin_browser_manager.login()
        logger.info(f"抖音登录操作完成: {result}")
        return result
    except Exception as e:
        error_msg = f"抖音登录失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def check_douyin_login_status():
    """检查抖音登录状态"""
    try:
        is_logged_in = await douyin_browser_manager.login_manager.check_login_status(force_check=True)
        
        if is_logged_in:
            session_info = douyin_browser_manager.login_manager.get_session_info()
            return f"抖音登录状态：已登录\n会话信息：{session_info}"
        else:
            return "抖音登录状态：未登录"
            
    except Exception as e:
        error_msg = f"检查抖音登录状态失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def clear_douyin_login():
    """清除抖音登录状态"""
    try:
        await douyin_browser_manager.login_manager.clear_login_state()
        douyin_browser_manager.is_logged_in = False
        return "抖音登录状态已清除"
        
    except Exception as e:
        error_msg = f"清除抖音登录状态失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_douyin_user_info():
    """获取当前登录用户的抖音信息"""
    try:
        # 确保已登录
        if not douyin_browser_manager.is_logged_in:
            login_result = await douyin_browser_manager.login()
            if "成功" not in login_result:
                return f"登录失败: {login_result}"
        
        # 访问个人主页
        await douyin_browser_manager.goto("https://www.douyin.com/user/self")
        
        # 获取用户信息
        user_info = await douyin_browser_manager.main_page.evaluate('''
            () => {
                // 尝试获取用户名
                let username = "未知用户";
                const usernameSelectors = [
                    '.username', 
                    '.user-name', 
                    '[data-e2e="user-title"]',
                    '.account-name'
                ];
                
                for (const selector of usernameSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim()) {
                        username = el.textContent.trim();
                        break;
                    }
                }
                
                // 尝试获取粉丝数
                let followers = "未知";
                const followerSelectors = [
                    '[data-e2e="fans-num"]',
                    '.follower-count',
                    '.fans-num'
                ];
                
                for (const selector of followerSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim()) {
                        followers = el.textContent.trim();
                        break;
                    }
                }
                
                // 尝试获取关注数
                let following = "未知";
                const followingSelectors = [
                    '[data-e2e="follow-num"]',
                    '.following-count',
                    '.follow-num'
                ];
                
                for (const selector of followingSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim()) {
                        following = el.textContent.trim();
                        break;
                    }
                }
                
                return {
                    username: username,
                    followers: followers,
                    following: following,
                    url: window.location.href
                };
            }
        ''')
        
        result = f"抖音用户信息：\n"
        result += f"用户名：{user_info['username']}\n"
        result += f"粉丝数：{user_info['followers']}\n"
        result += f"关注数：{user_info['following']}\n"
        result += f"主页链接：{user_info['url']}"
        
        return result
        
    except Exception as e:
        error_msg = f"获取抖音用户信息失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def search_douyin_videos(keywords: str, limit: int = 5):
    """搜索抖音视频
    
    Args:
        keywords: 搜索关键词
        limit: 返回结果数量限制
    """
    try:
        # 确保已登录
        if not douyin_browser_manager.is_logged_in:
            login_result = await douyin_browser_manager.login()
            if "成功" not in login_result:
                return f"登录失败: {login_result}"
        
        # 访问搜索页面
        search_url = f"https://www.douyin.com/search/{keywords}"
        await douyin_browser_manager.goto(search_url)
        
        # 等待搜索结果加载
        await asyncio.sleep(3)
        
        # 获取搜索结果
        videos = await douyin_browser_manager.main_page.evaluate(f'''
            () => {{
                const videos = [];
                const videoElements = document.querySelectorAll('[data-e2e="search-result"], .video-item');
                
                for (let i = 0; i < Math.min(videoElements.length, {limit}); i++) {{
                    const element = videoElements[i];
                    
                    // 获取标题
                    let title = "未知标题";
                    const titleEl = element.querySelector('.title, [data-e2e="video-title"], .desc');
                    if (titleEl) {{
                        title = titleEl.textContent.trim();
                    }}
                    
                    // 获取作者
                    let author = "未知作者";
                    const authorEl = element.querySelector('.author, [data-e2e="video-author"], .username');
                    if (authorEl) {{
                        author = authorEl.textContent.trim();
                    }}
                    
                    // 获取链接
                    let url = "";
                    const linkEl = element.querySelector('a');
                    if (linkEl) {{
                        url = linkEl.href;
                    }}
                    
                    if (title !== "未知标题" && url) {{
                        videos.push({{
                            title: title,
                            author: author,
                            url: url
                        }});
                    }}
                }}
                
                return videos;
            }}
        ''')
        
        if not videos:
            return f"未找到与'{keywords}'相关的抖音视频"
        
        # 格式化返回结果
        result = f"找到 {len(videos)} 个与'{keywords}'相关的抖音视频：\n\n"
        for i, video in enumerate(videos, 1):
            result += f"{i}. {video['title']}\n"
            result += f"   作者：{video['author']}\n"
            result += f"   链接：{video['url']}\n\n"
        
        return result
        
    except Exception as e:
        error_msg = f"搜索抖音视频失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool()
async def get_douyin_video_info(url: str):
    """获取抖音视频详细信息
    
    Args:
        url: 抖音视频链接
    """
    try:
        # 确保已登录
        if not douyin_browser_manager.is_logged_in:
            login_result = await douyin_browser_manager.login()
            if "成功" not in login_result:
                return f"登录失败: {login_result}"
        
        # 访问视频页面
        await douyin_browser_manager.goto(url)
        
        # 获取视频信息
        video_info = await douyin_browser_manager.main_page.evaluate('''
            () => {
                // 获取视频标题/描述
                let title = "未知标题";
                const titleSelectors = [
                    '[data-e2e="video-desc"]',
                    '.video-desc',
                    '.desc-text'
                ];
                
                for (const selector of titleSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim()) {
                        title = el.textContent.trim();
                        break;
                    }
                }
                
                // 获取作者信息
                let author = "未知作者";
                const authorSelectors = [
                    '[data-e2e="video-author"]',
                    '.author-name',
                    '.username'
                ];
                
                for (const selector of authorSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim()) {
                        author = el.textContent.trim();
                        break;
                    }
                }
                
                // 获取点赞数
                let likes = "未知";
                const likeSelectors = [
                    '[data-e2e="like-count"]',
                    '.like-count',
                    '.digg-count'
                ];
                
                for (const selector of likeSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent.trim()) {
                        likes = el.textContent.trim();
                        break;
                    }
                }
                
                return {
                    title: title,
                    author: author,
                    likes: likes,
                    url: window.location.href
                };
            }
        ''')
        
        result = f"抖音视频信息：\n"
        result += f"标题/描述：{video_info['title']}\n"
        result += f"作者：{video_info['author']}\n"
        result += f"点赞数：{video_info['likes']}\n"
        result += f"链接：{video_info['url']}"
        
        return result
        
    except Exception as e:
        error_msg = f"获取抖音视频信息失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def main():
    """主函数入口"""
    try:
        logger.info("启动抖音 MCP 服务器...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭抖音 MCP 服务器...")
        asyncio.run(cleanup_resources())
    except Exception as e:
        logger.error(f"抖音 MCP 服务器运行出错: {str(e)}")
        asyncio.run(cleanup_resources())
        raise

if __name__ == "__main__":
    main()
