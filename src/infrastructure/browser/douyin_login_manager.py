"""
抖音登录状态管理器
"""
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from src.core.config.config import config
from src.core.logging.logger import logger


class DouyinLoginManager:
    """抖音登录状态管理器"""

    def __init__(self, browser_manager):
        """初始化登录状态管理器

        Args:
            browser_manager: 抖音浏览器管理器实例
        """
        self.browser = browser_manager
        self.login_state_file = config.paths.browser_data_dir / "douyin_login_state.json"
        self.cookie_backup_dir = config.paths.browser_data_dir / "douyin_cookie_backups"
        self.cookie_backup_dir.mkdir(parents=True, exist_ok=True)

        # 登录状态跟踪
        self._last_login_check = 0
        self._last_cookie_backup = 0
        self._login_attempts = 0
        self._session_start_time = None

    async def save_login_state(self, login_info: Dict[str, Any] = None):
        """保存登录状态信息

        Args:
            login_info: 额外的登录信息
        """
        try:
            state_data = {
                "login_time": datetime.now().isoformat(),
                "session_id": str(int(time.time())),
                "browser_data_dir": str(self.browser.data_dir),
                "login_attempts": self._login_attempts,
                "last_activity": datetime.now().isoformat(),
                "auto_login_enabled": True,
                "login_info": login_info or {}
            }

            with open(self.login_state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            logger.info("抖音登录状态已保存")

            # 同时备份cookies
            await self._backup_cookies()

        except Exception as e:
            logger.error(f"保存抖音登录状态失败: {str(e)}")

    async def load_login_state(self) -> Optional[Dict[str, Any]]:
        """加载登录状态信息

        Returns:
            登录状态数据，如果不存在或过期则返回None
        """
        try:
            if not self.login_state_file.exists():
                logger.info("未找到抖音登录状态文件")
                return None

            with open(self.login_state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            # 检查登录状态是否过期（30天）
            login_time = datetime.fromisoformat(state_data["login_time"])
            max_retention = timedelta(days=30)

            if datetime.now() - login_time > max_retention:
                logger.warning("抖音登录状态已过期，需要重新登录")
                await self.clear_login_state()
                return None

            logger.info(f"加载抖音登录状态成功，登录时间: {login_time}")
            return state_data

        except Exception as e:
            logger.error(f"加载抖音登录状态失败: {str(e)}")
            return None

    async def clear_login_state(self):
        """清除登录状态"""
        try:
            if self.login_state_file.exists():
                self.login_state_file.unlink()
                logger.info("抖音登录状态已清除")

            # 重置计数器
            self._login_attempts = 0
            self._session_start_time = None

        except Exception as e:
            logger.error(f"清除抖音登录状态失败: {str(e)}")

    async def check_login_status(self, force_check: bool = False) -> bool:
        """检查当前登录状态

        Args:
            force_check: 是否强制检查（忽略检查间隔）

        Returns:
            是否已登录
        """
        current_time = time.time()
        check_interval = 300  # 5分钟检查一次

        # 检查是否需要执行检查
        if not force_check and (current_time - self._last_login_check < check_interval):
            return self.browser.is_logged_in

        try:
            # 确保浏览器已启动并健康
            await self.browser.ensure_browser()

            # 验证页面是否仍然有效
            if not self.browser.main_page:
                logger.warning("抖音主页面不存在，重新确保浏览器")
                await self.browser.ensure_browser(force_check=True)

            # 检查页面是否已关闭
            try:
                if hasattr(self.browser.main_page, 'is_closed'):
                    # 修复：is_closed()可能是同步方法
                    try:
                        is_closed = self.browser.main_page.is_closed()
                        # 如果返回的是协程，则await它
                        if hasattr(is_closed, '__await__'):
                            is_closed = await is_closed
                    except Exception:
                        # 如果调用失败，尝试异步调用
                        try:
                            is_closed = await self.browser.main_page.is_closed()
                        except Exception:
                            # 如果都失败，假设页面未关闭
                            is_closed = False

                    if is_closed:
                        logger.warning("抖音页面已关闭，重新启动浏览器")
                        await self.browser.ensure_browser(force_check=True)
                else:
                    # 如果没有 is_closed 方法，尝试访问页面URL来检查
                    try:
                        current_url = self.browser.main_page.url
                        logger.debug(f"页面URL检查成功: {current_url}")
                    except Exception:
                        logger.warning("抖音页面无法访问，重新启动浏览器")
                        await self.browser.ensure_browser(force_check=True)
            except Exception as e:
                logger.warning(f"检查抖音页面状态失败: {str(e)}，重新启动浏览器")
                await self.browser.ensure_browser(force_check=True)

            # 访问抖音首页检查登录状态
            try:
                current_url = self.browser.main_page.url
                if not current_url.startswith("https://www.douyin.com"):
                    await self.browser.goto("https://www.douyin.com")
            except Exception as e:
                logger.warning(f"获取当前URL失败: {str(e)}，直接访问首页")
                await self.browser.goto("https://www.douyin.com")

            # 等待页面加载
            await asyncio.sleep(2)

            # 安全地检查是否有登录按钮
            try:
                login_elements = await self.browser.main_page.query_selector_all('text="登录"')
                is_logged_in = len(login_elements) == 0
            except Exception as e:
                logger.error(f"查询抖音登录元素失败: {str(e)}")
                # 如果查询失败，假设未登录
                is_logged_in = False

            # 更新状态
            self.browser.is_logged_in = is_logged_in
            self._last_login_check = current_time

            if is_logged_in:
                logger.info("抖音登录状态检查：已登录")
                # 更新活动时间
                await self._update_last_activity()
            else:
                logger.warning("抖音登录状态检查：未登录")

            return is_logged_in

        except Exception as e:
            logger.error(f"检查抖音登录状态时出错: {str(e)}")
            # 出错时标记为未登录，避免后续操作失败
            self.browser.is_logged_in = False
            return False

    async def auto_restore_login(self) -> bool:
        """自动恢复登录状态

        Returns:
            恢复是否成功
        """
        try:
            # 加载登录状态
            login_state = await self.load_login_state()
            if not login_state:
                logger.info("没有可恢复的抖音登录状态")
                return False

            # 启动浏览器
            await self.browser.ensure_browser()

            # 关键修复：加载保存的cookies
            await self._restore_cookies()

            # 检查登录状态
            if await self.check_login_status(force_check=True):
                logger.info("自动恢复抖音登录状态成功")
                self._session_start_time = datetime.now()
                self.browser.is_logged_in = True
                return True
            else:
                logger.warning("自动恢复抖音登录状态失败，可能需要重新登录")
                return False

        except Exception as e:
            logger.error(f"自动恢复抖音登录状态时出错: {str(e)}")
            return False

    async def _restore_cookies(self):
        """恢复保存的cookies"""
        try:
            # 查找最新的cookies备份文件
            backup_files = sorted(self.cookie_backup_dir.glob("douyin_cookies_*.json"))
            if backup_files:
                latest_backup = backup_files[-1]
                logger.info(f"尝试恢复cookies: {latest_backup}")

                # 加载cookies
                success = await self.browser.load_cookies(str(latest_backup))
                if success:
                    logger.info("✅ 抖音cookies恢复成功")
                else:
                    logger.warning("⚠️ 抖音cookies恢复失败")
            else:
                logger.info("未找到可恢复的抖音cookies备份")

        except Exception as e:
            logger.error(f"恢复抖音cookies失败: {str(e)}")

    async def _backup_cookies(self):
        """备份当前的cookies"""
        try:
            current_time = time.time()
            backup_interval = 3600  # 1小时备份一次

            # 检查是否需要备份
            if current_time - self._last_cookie_backup < backup_interval:
                return

            # 保存到备份文件
            backup_filename = f"douyin_cookies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = self.cookie_backup_dir / backup_filename

            await self.browser.save_cookies(str(backup_path))

            # 清理旧备份（保留最近5个）
            backup_files = sorted(self.cookie_backup_dir.glob("douyin_cookies_*.json"))
            if len(backup_files) > 5:
                for old_backup in backup_files[:-5]:
                    old_backup.unlink()

            self._last_cookie_backup = current_time
            logger.debug(f"抖音 Cookies已备份到: {backup_path}")

        except Exception as e:
            logger.error(f"备份抖音 cookies失败: {str(e)}")

    async def _update_last_activity(self):
        """更新最后活动时间"""
        try:
            if self.login_state_file.exists():
                with open(self.login_state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)

                state_data["last_activity"] = datetime.now().isoformat()

                with open(self.login_state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.debug(f"更新抖音活动时间失败: {str(e)}")

    async def login(self) -> str:
        """智能登录，优先尝试恢复，失败后引导用户登录

        Returns:
            登录结果消息
        """
        try:
            # 首先尝试自动恢复
            logger.info("尝试自动恢复抖音登录状态...")
            if await self.auto_restore_login():
                return "已自动恢复抖音登录状态"

            # 自动恢复失败，进行手动登录
            logger.info("自动恢复失败，开始抖音手动登录流程")

            # 确保浏览器已启动并健康
            await self.browser.ensure_browser()

            # 验证页面状态
            if not self.browser.main_page:
                logger.error("抖音浏览器页面未正确初始化")
                return "浏览器初始化失败，请重试"

            # 安全地访问抖音创作者中心
            try:
                current_url = self.browser.main_page.url
                if not current_url.startswith("https://creator.douyin.com"):
                    await self.browser.main_page.goto("https://creator.douyin.com", timeout=60000)
                    await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"访问创作者中心失败: {str(e)}，尝试重新启动浏览器")
                await self.browser.ensure_browser(force_check=True)
                await self.browser.main_page.goto("https://creator.douyin.com", timeout=60000)
                await asyncio.sleep(3)

            # 检查是否需要登录
            need_login = await self._check_if_need_login()
            if need_login:
                # 提示用户手动登录
                message = "请在打开的浏览器窗口中完成抖音登录操作。登录成功后，系统将自动继续。"
                print(message)
                logger.info("等待用户抖音登录")

                # 等待用户登录成功
                max_wait_time = 180  # 等待3分钟
                wait_interval = 5
                waited_time = 0

                while waited_time < max_wait_time:
                    try:
                        # 检查页面是否仍然有效
                        if hasattr(self.browser.main_page, 'is_closed'):
                            try:
                                is_closed = self.browser.main_page.is_closed()
                                if hasattr(is_closed, '__await__'):
                                    is_closed = await is_closed
                                if is_closed:
                                    logger.error("页面在等待登录过程中被关闭")
                                    return "页面已关闭，请重新尝试登录"
                            except Exception:
                                pass

                        # 检查是否已登录成功
                        if not await self._check_if_need_login():
                            self.browser.is_logged_in = True
                            await asyncio.sleep(2)  # 等待页面加载

                            # 保存登录状态
                            await self.save_login_state({
                                "login_method": "manual_scan",
                                "login_time": datetime.now().isoformat(),
                                "platform": "douyin"
                            })
                            self._session_start_time = datetime.now()

                            logger.info("用户抖音登录成功")
                            return "抖音登录成功！"
                    except Exception as e:
                        logger.warning(f"检查抖音登录状态时出错: {str(e)}")
                        # 如果查询失败，可能是页面问题，尝试恢复
                        try:
                            await self.browser.ensure_browser(force_check=True)
                        except Exception:
                            pass

                    # 继续等待
                    await asyncio.sleep(wait_interval)
                    waited_time += wait_interval

                return "抖音登录等待超时。请重试或检查网络连接。"
            else:
                # 没有找到登录元素，可能已经登录
                self.browser.is_logged_in = True
                await self.save_login_state({
                    "login_method": "already_logged_in",
                    "login_time": datetime.now().isoformat(),
                    "platform": "douyin"
                })
                return "已登录抖音账号"

        except Exception as e:
            logger.error(f"抖音登录过程出错: {str(e)}")
            return f"登录过程出错: {str(e)}"

    async def _check_if_need_login(self) -> bool:
        """检查是否需要登录"""
        try:
            # 检查页面中是否有登录相关元素
            login_indicators = [
                'text="登录"',
                'text="我是创作者"',
                'text="扫码登录"',
                'text="手机号登录"',
                'text="验证码登录"',
                '.login-btn',
                '.qr-code',
                'input[name*="login"]',
                'input[placeholder*="手机号"]',
                'input[placeholder*="验证码"]'
            ]

            found_login_elements = 0
            for selector in login_indicators:
                try:
                    elements = await self.browser.main_page.query_selector_all(selector)
                    if elements:
                        found_login_elements += 1
                        logger.debug(f"找到登录元素: {selector}")
                except Exception:
                    continue

            # 如果找到多个登录相关元素，说明在登录页面
            need_login = found_login_elements >= 2

            # 额外检查：查看页面标题
            try:
                title = await self.browser.main_page.title()
                if any(keyword in title for keyword in ["登录", "Login", "创作者"]):
                    need_login = True
                    logger.debug(f"页面标题包含登录关键词: {title}")
            except Exception:
                pass

            logger.debug(f"登录检查结果: 需要登录={need_login}, 找到登录元素={found_login_elements}")
            return need_login

        except Exception as e:
            logger.warning(f"检查登录需求失败: {str(e)}")
            return True  # 出错时假设需要登录

    def get_session_info(self) -> Dict[str, Any]:
        """获取当前会话信息"""
        return {
            "is_logged_in": self.browser.is_logged_in,
            "session_start_time": self._session_start_time.isoformat() if self._session_start_time else None,
            "login_attempts": self._login_attempts,
            "last_login_check": self._last_login_check,
            "last_cookie_backup": self._last_cookie_backup,
            "login_state_file_exists": self.login_state_file.exists()
        }
