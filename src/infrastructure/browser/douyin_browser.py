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
        self.data_dir = config.paths.browser_data_dir / "douyin_data"

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
                    # 注意：is_closed 是属性，不是方法
                    is_closed = self.main_page.is_closed()
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
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )

            # 创建浏览器上下文（使用持久化上下文）
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                storage_state=None  # 可以后续加载保存的状态
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
        """关闭浏览器并清理资源"""
        import os
        import psutil
        import subprocess
        import shutil

        try:
            logger.info("执行抖音浏览器关闭")

            # 1. 保存登录状态（如果已登录）
            if hasattr(self, 'is_logged_in') and self.is_logged_in:
                try:
                    if hasattr(self, 'login_manager'):
                        await self.login_manager.save_login_state({
                            "close_reason": "browser_close",
                            "close_time": datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.warning(f"保存抖音登录状态失败: {str(e)}")

            # 2. 尝试正常关闭页面
            if self.main_page:
                try:
                    await self.main_page.close()
                    logger.info("抖音主页面正常关闭")
                except Exception as e:
                    logger.warning(f"关闭抖音主页面时出错: {str(e)}")
                finally:
                    self.main_page = None

            # 3. 关闭浏览器上下文
            if self.context:
                try:
                    await self.context.close()
                    logger.info("抖音浏览器上下文正常关闭")
                except Exception as e:
                    logger.warning(f"关闭抖音浏览器上下文时出错: {str(e)}")
                finally:
                    self.context = None

            # 4. 关闭浏览器实例
            if self.browser:
                try:
                    await self.browser.close()
                    logger.info("抖音浏览器实例正常关闭")
                except Exception as e:
                    logger.warning(f"关闭抖音浏览器实例时出错: {str(e)}")
                finally:
                    self.browser = None

            # 5. 停止Playwright实例
            if self.playwright:
                try:
                    await self.playwright.stop()
                    logger.info("抖音Playwright实例停止")
                except Exception as e:
                    logger.warning(f"停止抖音Playwright实例时出错: {str(e)}")
                finally:
                    self.playwright = None

            # 6. 强制清理浏览器进程（确保完全释放）
            try:
                # 查找并终止所有与douyin相关的Chromium进程
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline', [])
                        cmdline_str = ' '.join(cmdline) if cmdline else ''

                        if ('chromium' in proc.info['name'].lower() or 'chrome' in proc.info['name'].lower()) and 'douyin_data' in cmdline_str:
                            logger.info(f"终止剩余的抖音浏览器进程: PID {proc.info['pid']}")
                            psutil.Process(proc.info['pid']).terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass

                # 使用系统命令进行最终清理
                if os.name == 'posix':  # macOS/Linux
                    subprocess.run(['pkill', '-f', 'chromium.*douyin_data'], stderr=subprocess.PIPE)
                elif os.name == 'nt':   # Windows
                    subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], stderr=subprocess.PIPE)
            except Exception as e:
                logger.warning(f"强制清理抖音浏览器进程时出错: {str(e)}")

            # 7. 清理锁文件
            try:
                lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie"]
                for lock_file in lock_files:
                    lock_path = self.data_dir / lock_file
                    if lock_path.exists():
                        if lock_path.is_file():
                            lock_path.unlink()
                        elif lock_path.is_dir():
                            shutil.rmtree(lock_path)
                        logger.info(f"清理了抖音{lock_file}文件")
            except Exception as e:
                logger.warning(f"清理抖音锁文件时出错: {str(e)}")

            # 重置状态
            self.is_logged_in = False

            # 额外等待确保资源完全释放
            await asyncio.sleep(1)

            logger.info("抖音浏览器资源清理完成")

        except Exception as e:
            logger.error(f"关闭抖音浏览器失败: {str(e)}")
            # 即使关闭失败，也要重置状态
            self.main_page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self.is_logged_in = False

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
                # 等待页面完全加载
                await asyncio.sleep(3)

                # 尝试多种登录按钮选择器
                login_selectors = [
                    'text="登录"',
                    '[data-e2e="login-button"]',
                    '.login-button',
                    'button:has-text("登录")',
                    'a:has-text("登录")'
                ]

                login_element = None
                for selector in login_selectors:
                    try:
                        login_element = await self.main_page.wait_for_selector(selector, timeout=5000)
                        if login_element:
                            logger.info(f"找到登录按钮，使用选择器: {selector}")
                            break
                    except Exception:
                        continue

                if login_element:
                    # 滚动到元素位置
                    await login_element.scroll_into_view_if_needed()
                    await asyncio.sleep(1)

                    # 尝试点击，如果被拦截则使用 JavaScript 点击
                    try:
                        await login_element.click(timeout=10000)
                    except Exception as e:
                        logger.warning(f"普通点击失败，尝试 JavaScript 点击: {str(e)}")
                        await self.main_page.evaluate('(element) => element.click()', login_element)

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
                                # 注意：is_closed 是属性，不是方法
                                is_closed = self.main_page.is_closed()
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
