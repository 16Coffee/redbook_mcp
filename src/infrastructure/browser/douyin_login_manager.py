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

            # 启动浏览器（会自动加载保存的cookies和session）
            await self.browser.ensure_browser()

            # 检查登录状态
            if await self.check_login_status(force_check=True):
                logger.info("自动恢复抖音登录状态成功")
                self._session_start_time = datetime.now()
                return True
            else:
                logger.warning("自动恢复抖音登录状态失败，可能需要重新登录")
                return False

        except Exception as e:
            logger.error(f"自动恢复抖音登录状态时出错: {str(e)}")
            return False

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

    async def login(self) -> bool:
        """手动登录流程

        Returns:
            登录是否成功
        """
        try:
            logger.info("开始抖音手动登录流程...")

            # 确保浏览器启动
            await self.browser.ensure_browser()

            # 导航到创作者中心登录页面
            await self.browser.goto("https://creator.douyin.com")
            await asyncio.sleep(3)

            # 检查是否已经登录
            current_url = self.browser.main_page.url
            logger.info(f"当前页面URL: {current_url}")

            # 如果URL包含登录相关路径，说明需要登录
            if "login" in current_url.lower() or "creator.douyin.com" in current_url:
                logger.info("检测到登录页面，等待用户手动登录...")

                # 等待用户手动登录（检查URL变化或登录元素消失）
                max_wait_time = 300  # 5分钟超时
                start_time = time.time()

                while time.time() - start_time < max_wait_time:
                    await asyncio.sleep(2)

                    try:
                        current_url = self.browser.main_page.url

                        # 检查是否跳转到了主页面或其他非登录页面
                        if "login" not in current_url.lower():
                            logger.info("检测到页面跳转，可能已登录")
                            break

                        # 检查登录按钮是否消失
                        login_elements = await self.browser.main_page.query_selector_all('text="登录"')
                        if len(login_elements) == 0:
                            logger.info("登录按钮消失，可能已登录")
                            break

                    except Exception as e:
                        logger.debug(f"检查登录状态时出错: {str(e)}")
                        continue

                # 验证登录状态
                if await self.check_login_status(force_check=True):
                    logger.info("✅ 手动登录成功")
                    self._session_start_time = datetime.now()
                    self._login_attempts += 1

                    # 保存登录状态
                    await self.save_login_state({
                        "login_method": "manual_login",
                        "login_time": datetime.now().isoformat(),
                        "platform": "douyin"
                    })

                    return True
                else:
                    logger.warning("❌ 手动登录失败或超时")
                    return False
            else:
                # 可能已经登录了
                if await self.check_login_status(force_check=True):
                    logger.info("✅ 检测到已登录状态")
                    return True
                else:
                    logger.warning("❌ 未检测到登录状态")
                    return False

        except Exception as e:
            logger.error(f"手动登录过程中出错: {str(e)}")
            return False

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
