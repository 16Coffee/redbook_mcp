"""
登录状态管理器，负责登录状态的持久化、恢复和监控
"""
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from src.core.config.config import config
from src.core.logging.logger import logger


class LoginStateManager:
    """登录状态管理器"""
    
    def __init__(self, browser_manager):
        """初始化登录状态管理器
        
        Args:
            browser_manager: 浏览器管理器实例
        """
        self.browser = browser_manager
        self.login_state_file = config.paths.data_dir / "login_state.json"
        self.cookie_backup_dir = config.paths.data_dir / "cookie_backups"
        self.cookie_backup_dir.mkdir(exist_ok=True)
        
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
                "browser_data_dir": str(config.paths.browser_data_dir),
                "login_attempts": self._login_attempts,
                "last_activity": datetime.now().isoformat(),
                "auto_login_enabled": True,
                "login_info": login_info or {}
            }
            
            with open(self.login_state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            logger.info("登录状态已保存")
            
            # 同时备份cookies
            if config.login_persistence["session_backup_enabled"]:
                await self._backup_cookies()
                
        except Exception as e:
            logger.error(f"保存登录状态失败: {str(e)}")
    
    async def load_login_state(self) -> Optional[Dict[str, Any]]:
        """加载登录状态信息
        
        Returns:
            登录状态数据，如果不存在或过期则返回None
        """
        try:
            if not self.login_state_file.exists():
                logger.info("未找到登录状态文件")
                return None
            
            with open(self.login_state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # 检查登录状态是否过期
            login_time = datetime.fromisoformat(state_data["login_time"])
            max_retention = timedelta(days=config.login_persistence["max_login_retention_days"])
            
            if datetime.now() - login_time > max_retention:
                logger.warning("登录状态已过期，需要重新登录")
                await self.clear_login_state()
                return None
            
            logger.info(f"加载登录状态成功，登录时间: {login_time}")
            return state_data
            
        except Exception as e:
            logger.error(f"加载登录状态失败: {str(e)}")
            return None
    
    async def clear_login_state(self):
        """清除登录状态"""
        try:
            if self.login_state_file.exists():
                self.login_state_file.unlink()
                logger.info("登录状态已清除")
            
            # 重置计数器
            self._login_attempts = 0
            self._session_start_time = None
            
        except Exception as e:
            logger.error(f"清除登录状态失败: {str(e)}")
    
    async def check_login_status(self, force_check: bool = False) -> bool:
        """检查当前登录状态
        
        Args:
            force_check: 是否强制检查（忽略检查间隔）
        
        Returns:
            是否已登录
        """
        current_time = time.time()
        check_interval = config.login_persistence["session_check_interval"]
        
        # 检查是否需要执行检查
        if not force_check and (current_time - self._last_login_check < check_interval):
            return self.browser.is_logged_in
        
        try:
            # 确保浏览器已启动
            if not self.browser.main_page:
                await self.browser.ensure_browser()
            
            # 访问小红书首页检查登录状态
            current_url = self.browser.main_page.url
            if not current_url.startswith("https://www.xiaohongshu.com"):
                await self.browser.goto("https://www.xiaohongshu.com", wait_time=3)
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 检查是否有登录按钮
            login_elements = await self.browser.main_page.query_selector_all('text="登录"')
            is_logged_in = len(login_elements) == 0
            
            # 更新状态
            self.browser.is_logged_in = is_logged_in
            self._last_login_check = current_time
            
            if is_logged_in:
                logger.info("登录状态检查：已登录")
                # 更新活动时间
                await self._update_last_activity()
            else:
                logger.warning("登录状态检查：未登录")
                
            return is_logged_in
            
        except Exception as e:
            logger.error(f"检查登录状态时出错: {str(e)}")
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
                logger.info("没有可恢复的登录状态")
                return False
            
            # 确保浏览器使用正确的数据目录
            expected_data_dir = login_state.get("browser_data_dir")
            current_data_dir = str(config.paths.browser_data_dir)
            
            if expected_data_dir != current_data_dir:
                logger.warning(f"浏览器数据目录不匹配: 期望 {expected_data_dir}, 当前 {current_data_dir}")
            
            # 启动浏览器（会自动加载保存的cookies和session）
            await self.browser.ensure_browser()
            
            # 检查登录状态
            if await self.check_login_status(force_check=True):
                logger.info("自动恢复登录状态成功")
                self._session_start_time = datetime.now()
                return True
            else:
                logger.warning("自动恢复登录状态失败，可能需要重新登录")
                return False
                
        except Exception as e:
            logger.error(f"自动恢复登录状态时出错: {str(e)}")
            return False
    
    async def smart_login(self) -> str:
        """智能登录，优先尝试恢复，失败后引导用户登录
        
        Returns:
            登录结果消息
        """
        try:
            # 首先尝试自动恢复
            logger.info("尝试自动恢复登录状态...")
            if await self.auto_restore_login():
                return "已自动恢复登录状态"
            
            # 自动恢复失败，进行手动登录
            logger.info("自动恢复失败，开始手动登录流程")
            
            # 确保浏览器已启动
            await self.browser.ensure_browser()
            
            # 访问小红书首页
            if not self.browser.main_page.url.startswith("https://www.xiaohongshu.com"):
                await self.browser.main_page.goto("https://www.xiaohongshu.com", timeout=60000)
                await asyncio.sleep(3)
            
            # 查找登录按钮并点击
            login_elements = await self.browser.main_page.query_selector_all('text="登录"')
            if login_elements:
                await login_elements[0].click()
                
                # 提示用户手动登录
                message = "请在打开的浏览器窗口中完成登录操作。登录成功后，系统将自动继续。"
                print(message)
                logger.info("等待用户登录")
            
                # 等待用户登录成功
                max_wait_time = 180  # 等待3分钟
                wait_interval = 5
                waited_time = 0
                
                while waited_time < max_wait_time:
                    # 检查是否已登录成功
                    still_login = await self.browser.main_page.query_selector_all('text="登录"')
                    if not still_login:
                        self.browser.is_logged_in = True
                        await asyncio.sleep(2)  # 等待页面加载
                        
                        # 保存登录状态
                        await self.save_login_state({
                            "login_method": "manual_scan",
                            "login_time": datetime.now().isoformat()
                        })
                        self._session_start_time = datetime.now()
                        
                        logger.info("用户登录成功")
                        return "登录成功！"
                    
                    # 继续等待
                    await asyncio.sleep(wait_interval)
                    waited_time += wait_interval
                
                return "登录等待超时。请重试或检查网络连接。"
            else:
                # 没有找到登录按钮，可能已经登录
                self.browser.is_logged_in = True
                await self.save_login_state({
                    "login_method": "already_logged_in",
                    "login_time": datetime.now().isoformat()
                })
                return "已登录小红书账号"
            
        except Exception as e:
            logger.error(f"智能登录过程出错: {str(e)}")
            return f"登录过程出错: {str(e)}"
    
    async def _backup_cookies(self):
        """备份当前的cookies"""
        try:
            current_time = time.time()
            backup_interval = config.login_persistence["cookie_backup_interval"]
            
            # 检查是否需要备份
            if current_time - self._last_cookie_backup < backup_interval:
                return
            
            if not self.browser.browser_context:
                return
            
            # 获取所有cookies
            cookies = await self.browser.browser_context.cookies()
            
            # 保存到备份文件
            backup_filename = f"cookies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = self.cookie_backup_dir / backup_filename
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            # 清理旧备份（保留最近5个）
            backup_files = sorted(self.cookie_backup_dir.glob("cookies_*.json"))
            if len(backup_files) > 5:
                for old_backup in backup_files[:-5]:
                    old_backup.unlink()
            
            self._last_cookie_backup = current_time
            logger.debug(f"Cookies已备份到: {backup_path}")
            
        except Exception as e:
            logger.error(f"备份cookies失败: {str(e)}")
    
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
            logger.debug(f"更新活动时间失败: {str(e)}")
    
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