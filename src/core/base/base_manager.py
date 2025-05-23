"""
基础管理器类，提供公共的错误处理、日志记录等功能
"""
from abc import ABC, abstractmethod
from typing import Any
from src.core.logging.logger import logger
from src.core.exceptions.exceptions import RedBookMCPException
from src.core.base.decorators import performance_monitor, retry

class BaseManager(ABC):
    """基础管理器抽象类"""
    
    def __init__(self, name: str = None):
        """初始化基础管理器
        
        Args:
            name: 管理器名称
        """
        self.name = name or self.__class__.__name__
        self.logger = logger
    
    def log_info(self, message: str):
        """记录信息日志"""
        self.logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str):
        """记录错误日志"""
        self.logger.error(f"[{self.name}] {message}")
    
    def log_warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(f"[{self.name}] {message}")
    
    def log_debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(f"[{self.name}] {message}")
    
    def handle_error(self, error: Exception, operation: str = "操作") -> str:
        """统一错误处理
        
        Args:
            error: 异常对象
            operation: 操作描述
        
        Returns:
            str: 错误消息
        """
        error_msg = f"{operation}失败: {str(error)}"
        self.log_error(error_msg)
        
        if isinstance(error, RedBookMCPException):
            return error.message
        
        return error_msg
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化管理器（子类必须实现）
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod  
    async def cleanup(self):
        """清理资源（子类必须实现）"""
        pass

class BrowserBasedManager(BaseManager):
    """基于浏览器的管理器基类"""
    
    def __init__(self, browser_manager, name: str = None):
        """初始化基于浏览器的管理器
        
        Args:
            browser_manager: 浏览器管理器实例
            name: 管理器名称
        """
        super().__init__(name)
        self.browser = browser_manager
        self._last_browser_check = 0
        self._browser_check_interval = 60  # 60秒内不重复检查浏览器状态
    
    async def ensure_login(self, force_check=False) -> bool:
        """确保已登录，使用优化的检查策略
        
        Args:
            force_check: 是否强制检查浏览器状态
        
        Returns:
            bool: 是否已登录
        """
        try:
            # 优化：减少频繁的浏览器状态检查
            import time
            current_time = time.time()
            
            if not force_check and (current_time - self._last_browser_check < self._browser_check_interval):
                # 使用缓存的登录状态
                if hasattr(self.browser, 'is_logged_in') and self.browser.is_logged_in:
                    return True
            
            # 执行浏览器状态检查
            login_status = await self.browser.ensure_browser(force_check=force_check)
            self._last_browser_check = current_time
            
            if not login_status:
                self.log_warning("需要先登录小红书账号")
                return False
            return True
            
        except Exception as e:
            self.handle_error(e, "登录检查")
            return False
    
    async def safe_goto(self, url: str, wait_time: int = None, max_retries: int = 2) -> bool:
        """安全访问页面，使用优化的重试策略
        
        Args:
            url: 目标URL
            wait_time: 等待时间
            max_retries: 最大重试次数
        
        Returns:
            bool: 访问是否成功
        """
        try:
            # 优化：先检查浏览器健康状态，避免不必要的ensure_browser调用
            if not getattr(self.browser, '_browser_healthy', False):
                await self.ensure_login(force_check=True)
            
            success = await self.browser.goto(url, wait_time, max_retries)
            if success:
                self.log_info(f"成功访问: {url}")
            else:
                self.log_warning(f"访问失败: {url}")
            return success
            
        except Exception as e:
            self.handle_error(e, f"访问页面 {url}")
            return False 