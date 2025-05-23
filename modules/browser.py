"""
浏览器控制模块，负责浏览器实例的创建、页面访问和元素操作
"""
import asyncio
from playwright.async_api import async_playwright
from modules.config import (
    BROWSER_DATA_DIR, DEFAULT_TIMEOUT, DEFAULT_WAIT_TIME, 
    VIEWPORT_WIDTH, VIEWPORT_HEIGHT
)


class BrowserManager:
    """浏览器管理类，处理浏览器实例的创建、页面访问和元素操作"""
    
    def __init__(self):
        """初始化浏览器管理器"""
        self.browser_context = None
        self.main_page = None
        self.is_logged_in = False
        self.playwright_instance = None
    
    async def ensure_browser(self):
        """确保浏览器已启动且可用，自动检测并恢复失效对象"""
        if self.browser_context is None or await self._context_or_page_closed():
            await self.close()  # 清理旧对象
            await self._start_browser()
            # 仅在初始化时检查登录状态
            return await self._check_login_status()
        return self.is_logged_in

    async def _context_or_page_closed(self):
        """检测浏览器上下文或页面是否已关闭"""
        try:
            if self.browser_context is not None and hasattr(self.browser_context, "is_closed"):
                if await self.browser_context.is_closed():
                    return True
            if self.main_page is not None and hasattr(self.main_page, "is_closed"):
                if await self.main_page.is_closed():
                    return True
        except Exception:
            return True
        return False
    
    async def _start_browser(self):
        """启动浏览器并创建上下文"""
        # 启动浏览器
        self.playwright_instance = await async_playwright().start()
        
        # 使用持久化上下文来保存用户状态
        self.browser_context = await self.playwright_instance.chromium.launch_persistent_context(
            user_data_dir=BROWSER_DATA_DIR,
            headless=False,  # 非隐藏模式，方便用户登录
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            timeout=DEFAULT_TIMEOUT
        )
        
        # 创建一个新页面
        if self.browser_context.pages:
            self.main_page = self.browser_context.pages[0]
        else:
            self.main_page = await self.browser_context.new_page()
        
        # 设置页面级别的超时时间
        self.main_page.set_default_timeout(DEFAULT_TIMEOUT)
    
    async def _check_login_status(self):
        """检查登录状态
        
        Returns:
            bool: 是否已登录
        """
        # 仅访问首页检查登录状态
        if not self.main_page.url.startswith("https://www.xiaohongshu.com"):
            await self.main_page.goto("https://www.xiaohongshu.com", timeout=DEFAULT_TIMEOUT)
            await asyncio.sleep(DEFAULT_WAIT_TIME)
        
        # 检查是否已登录
        login_elements = await self.main_page.query_selector_all('text="登录"')
        if login_elements:
            self.is_logged_in = False
            return False  # 需要登录
        else:
            self.is_logged_in = True
            return True  # 已登录
    
    async def login(self):
        """登录小红书账号
        
        Returns:
            str: 登录结果消息
        """
        await self.ensure_browser()
        
        if self.is_logged_in:
            return "已登录小红书账号"
        
        # 如果当前不在小红书网站，则先访问小红书首页
        if not self.main_page.url.startswith("https://www.xiaohongshu.com"):
            await self.main_page.goto("https://www.xiaohongshu.com", timeout=DEFAULT_TIMEOUT)
            await asyncio.sleep(DEFAULT_WAIT_TIME)
        
        # 查找登录按钮并点击
        login_elements = await self.main_page.query_selector_all('text="登录"')
        if login_elements:
            await login_elements[0].click()
            
            # 提示用户手动登录
            message = "请在打开的浏览器窗口中完成登录操作。登录成功后，系统将自动继续。"
            print(message)
            
            # 等待用户登录成功
            max_wait_time = 180  # 等待3分钟
            wait_interval = 5
            waited_time = 0
            
            while waited_time < max_wait_time:
                # 检查是否已登录成功
                still_login = await self.main_page.query_selector_all('text="登录"')
                if not still_login:
                    self.is_logged_in = True
                    await asyncio.sleep(2)  # 等待页面加载
                    return "登录成功！"
                
                # 继续等待
                await asyncio.sleep(wait_interval)
                waited_time += wait_interval
            
            return "登录等待超时。请重试或手动登录后再使用其他功能。"
        else:
            self.is_logged_in = True
            return "已登录小红书账号"
    
    async def goto(self, url, wait_time=DEFAULT_WAIT_TIME):
        """访问指定URL并等待加载完成，同时处理可能出现的登录弹窗"""
        await self.ensure_browser()  # 每次操作前都确保对象有效
        try:
            await self.main_page.goto(url, timeout=DEFAULT_TIMEOUT)
            await asyncio.sleep(wait_time)  # 等待页面加载
            # 检查是否出现登录弹窗或登录提示
            await self._handle_login_popup()
            return True
        except Exception as e:
            print(f"访问页面出错: {str(e)}")
            # 若检测到对象已关闭，自动重启并重试一次
            if "has been closed" in str(e):
                await self.close()
                await self.ensure_browser()
                try:
                    await self.main_page.goto(url, timeout=DEFAULT_TIMEOUT)
                    await asyncio.sleep(wait_time)
                    await self._handle_login_popup()
                    return True
                except Exception as e2:
                    print(f"重试后仍访问页面出错: {str(e2)}")
            return False
    
    async def execute_scroll_script(self, script=None):
        """执行滚动脚本以加载更多内容
        
        Args:
            script (str, optional): 自定义滚动脚本. 默认为None.
        """
        if script is None:
            script = '''
                () => {
                    // 先滚动到页面底部
                    window.scrollTo(0, document.body.scrollHeight);
                    setTimeout(() => { 
                        // 然后滚动到中间
                        window.scrollTo(0, document.body.scrollHeight / 2); 
                    }, 1000);
                    setTimeout(() => { 
                        // 最后回到顶部
                        window.scrollTo(0, 0); 
                    }, 2000);
                }
            '''
        
        await self.main_page.evaluate(script)
        await asyncio.sleep(3)  # 等待滚动完成和内容加载
    
    async def get_page_content(self):
        """获取当前页面内容
        
        Returns:
            str: 页面HTML内容
        """
        return await self.main_page.content()
    
    async def _handle_login_popup(self):
        """处理页面上可能出现的登录弹窗
        
        Returns:
            bool: 是否处理了登录弹窗
        """
        # 检查是否出现登录弹窗或登录按钮
        login_elements = await self.main_page.query_selector_all('text="登录"')
        if login_elements and not self.is_logged_in:
            # 需要登录，执行登录流程
            await self.login()
            return True
        
        return False
        
    async def close(self):
        """关闭浏览器并清理资源"""
        if self.browser_context:
            await self.browser_context.close()
        
        if self.playwright_instance:
            await self.playwright_instance.stop()
