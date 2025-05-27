"""
抖音浏览器管理器
"""
import asyncio
import os
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.core.logging.logger import logger
from src.core.config.config import config


class DouyinBrowserManager:
    """抖音浏览器管理器"""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.main_page = None
        self.is_logged_in = False
        self.data_dir = Path(config.browser["data_dir"]) / "douyin_data"

        # 引入登录状态管理器（延迟初始化）
        self._login_manager = None

    @property
    def login_manager(self):
        """获取登录状态管理器（懒加载）"""
        if self._login_manager is None:
            from src.infrastructure.browser.douyin_login_manager import DouyinLoginManager
            self._login_manager = DouyinLoginManager(self)
        return self._login_manager

    async def ensure_browser(self, force_check: bool = False):
        """确保浏览器已启动并健康

        Args:
            force_check: 是否强制重新检查和启动
        """
        try:
            # 如果强制检查或浏览器未启动，重新启动
            if force_check or not self.browser or not self.context or not self.main_page:
                await self.start_browser()
                return True

            # 检查浏览器是否仍然有效
            try:
                if hasattr(self.main_page, 'is_closed'):
                    is_closed = await self.main_page.is_closed()
                    if is_closed:
                        logger.warning("抖音浏览器页面已关闭，重新启动")
                        await self.start_browser()
                        return True
            except Exception as e:
                logger.warning(f"检查抖音浏览器状态失败: {str(e)}，重新启动")
                await self.start_browser()
                return True

            return True

        except Exception as e:
            logger.error(f"确保抖音浏览器启动失败: {str(e)}")
            return False

    async def start_browser(self):
        """启动浏览器"""
        try:
            # 关闭现有浏览器
            await self.close_browser()

            # 确保数据目录存在
            self.data_dir.mkdir(parents=True, exist_ok=True)

            # 启动 Playwright
            self.playwright = await async_playwright().start()

            # 启动浏览器
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # 显示浏览器窗口
                user_data_dir=str(self.data_dir),
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )

            # 创建浏览器上下文
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            # 创建主页面
            self.main_page = await self.context.new_page()

            logger.info("抖音浏览器启动成功")
            return True

        except Exception as e:
            logger.error(f"启动抖音浏览器失败: {str(e)}")
            return False

    async def goto(self, url: str, wait_time: int = 3):
        """访问指定URL

        Args:
            url: 目标URL
            wait_time: 等待时间（秒）
        """
        try:
            await self.ensure_browser()
            await self.main_page.goto(url, timeout=60000)
            await asyncio.sleep(wait_time)
            logger.info(f"已访问抖音页面: {url}")

        except Exception as e:
            logger.error(f"访问抖音页面失败: {str(e)}")
            raise

    async def close_browser(self):
        """关闭浏览器"""
        try:
            if self.main_page:
                await self.main_page.close()
                self.main_page = None

            if self.context:
                await self.context.close()
                self.context = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            logger.info("抖音浏览器已关闭")

        except Exception as e:
            logger.error(f"关闭抖音浏览器失败: {str(e)}")

    async def save_cookies(self, file_path: str):
        """保存 cookies"""
        try:
            if self.context:
                cookies = await self.context.cookies()
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                logger.info(f"抖音 cookies 已保存到: {file_path}")

        except Exception as e:
            logger.error(f"保存抖音 cookies 失败: {str(e)}")

    async def load_cookies(self, file_path: str):
        """加载 cookies"""
        try:
            if self.context and os.path.exists(file_path):
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                logger.info(f"抖音 cookies 已加载: {file_path}")
                return True

        except Exception as e:
            logger.error(f"加载抖音 cookies 失败: {str(e)}")

        return False

    async def login(self) -> str:
        """智能登录抖音账号

        Returns:
            登录结果消息
        """
        try:
            logger.info("开始抖音登录流程...")

            # 首先尝试自动恢复登录状态
            logger.info("尝试自动恢复抖音登录状态...")
            if await self.login_manager.auto_restore_login():
                return "已自动恢复抖音登录状态"

            # 自动恢复失败，进行手动登录
            logger.info("自动恢复失败，开始手动登录流程")

            # 确保浏览器已启动并健康
            await self.ensure_browser()

            # 验证页面状态
            if not self.main_page:
                logger.error("浏览器页面未正确初始化")
                return "浏览器初始化失败，请重试"

            # 访问抖音首页
            try:
                current_url = self.main_page.url
                if not current_url.startswith("https://www.douyin.com"):
                    await self.goto("https://www.douyin.com")
            except Exception as e:
                logger.warning(f"访问抖音首页失败: {str(e)}，尝试重新启动浏览器")
                await self.ensure_browser(force_check=True)
                await self.goto("https://www.douyin.com")

            # 查找登录按钮并点击
            try:
                login_elements = await self.main_page.query_selector_all('text="登录"')
                if login_elements:
                    await login_elements[0].click()

                    # 提示用户手动登录
                    message = "请在打开的浏览器窗口中完成抖音登录操作。支持扫码登录或手机号登录。登录成功后，系统将自动继续。"
                    print(message)
                    logger.info("等待用户登录抖音")

                    # 等待用户登录成功
                    max_wait_time = 180  # 等待3分钟
                    wait_interval = 5
                    waited_time = 0

                    while waited_time < max_wait_time:
                        try:
                            # 检查页面是否仍然有效
                            if hasattr(self.main_page, 'is_closed'):
                                is_closed = await self.main_page.is_closed()
                                if is_closed:
                                    logger.error("页面在等待登录过程中被关闭")
                                    return "页面已关闭，请重新尝试登录"

                            # 检查是否已登录成功
                            still_login = await self.main_page.query_selector_all('text="登录"')
                            if not still_login:
                                self.is_logged_in = True
                                await asyncio.sleep(2)  # 等待页面加载

                                # 保存登录状态
                                await self.login_manager.save_login_state({
                                    "login_method": "manual_login",
                                    "login_time": datetime.now().isoformat(),
                                    "platform": "douyin"
                                })

                                logger.info("用户抖音登录成功")
                                return "抖音登录成功！"
                        except Exception as e:
                            logger.warning(f"检查抖音登录状态时出错: {str(e)}")
                            # 如果查询失败，可能是页面问题，尝试恢复
                            try:
                                await self.ensure_browser(force_check=True)
                            except Exception:
                                pass

                        # 继续等待
                        await asyncio.sleep(wait_interval)
                        waited_time += wait_interval

                    return "抖音登录等待超时。请重试或检查网络连接。"
                else:
                    # 没有找到登录按钮，可能已经登录
                    self.is_logged_in = True
                    await self.login_manager.save_login_state({
                        "login_method": "already_logged_in",
                        "login_time": datetime.now().isoformat(),
                        "platform": "douyin"
                    })
                    return "已登录抖音账号"

            except Exception as e:
                logger.error(f"查找抖音登录按钮失败: {str(e)}")
                return f"无法找到登录按钮: {str(e)}"

        except Exception as e:
            logger.error(f"抖音登录过程出错: {str(e)}")
            return f"登录过程出错: {str(e)}"

    def __del__(self):
        """析构函数"""
        try:
            if self.browser:
                asyncio.create_task(self.close_browser())
        except Exception:
            pass
