"""
装饰器模块，提供重试机制、性能监控等功能
"""
import asyncio
import time
from functools import wraps
from typing import Callable, Any
from src.core.logging.logger import logger
from src.core.exceptions.exceptions import RedBookMCPException

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间的倍数因子
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt == max_attempts:
                        logger.error(f"函数 {func.__name__} 在 {max_attempts} 次尝试后仍然失败: {str(e)}")
                        raise e
                    
                    logger.warning(f"函数 {func.__name__} 第 {attempt} 次尝试失败: {str(e)}，{current_delay}秒后重试")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        return wrapper
    return decorator

def performance_monitor(func: Callable) -> Callable:
    """性能监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"函数 {func.__name__} 执行时间: {execution_time:.2f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.2f}秒，错误: {str(e)}")
            raise e
    return wrapper

def validate_login(func: Callable) -> Callable:
    """登录验证装饰器"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs) -> Any:
        if not await self.browser.ensure_browser():
            raise RedBookMCPException("需要先登录小红书账号才能执行此操作")
        return await func(self, *args, **kwargs)
    return wrapper

def safe_execute(default_return: Any = None):
    """安全执行装饰器，捕获异常并返回默认值"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"函数 {func.__name__} 执行出错: {str(e)}")
                return default_return
        return wrapper
    return decorator 