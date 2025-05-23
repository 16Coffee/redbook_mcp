"""
智能等待机制模块，提供更高效的元素和条件等待
"""
import asyncio
from typing import Callable, Any, Optional, Union
from playwright.async_api import Page, Locator
from src.core.logging.logger import logger

class SmartWaiter:
    """智能等待器，提供各种等待策略"""
    
    def __init__(self, page: Page, default_timeout: int = 30000):
        """初始化智能等待器
        
        Args:
            page: Playwright页面对象
            default_timeout: 默认超时时间（毫秒）
        """
        self.page = page
        self.default_timeout = default_timeout
    
    async def wait_for_element(
        self, 
        selector: str, 
        timeout: Optional[int] = None,
        state: str = "visible"
    ) -> Optional[Locator]:
        """等待元素出现
        
        Args:
            selector: CSS选择器
            timeout: 超时时间（毫秒）
            state: 元素状态 ('visible', 'hidden', 'attached', 'detached')
        
        Returns:
            Optional[Locator]: 找到的元素，超时返回None
        """
        timeout = timeout or self.default_timeout
        try:
            await self.page.wait_for_selector(selector, timeout=timeout, state=state)
            return self.page.locator(selector)
        except Exception as e:
            logger.debug(f"等待元素 {selector} 超时: {str(e)}")
            return None
    
    async def wait_for_any_element(
        self, 
        selectors: list, 
        timeout: Optional[int] = None
    ) -> Optional[tuple]:
        """等待任意一个元素出现
        
        Args:
            selectors: CSS选择器列表
            timeout: 超时时间（毫秒）
        
        Returns:
            Optional[tuple]: (选择器, 元素) 或 None
        """
        timeout = timeout or self.default_timeout
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element and await element.is_visible():
                        return (selector, element)
                except Exception:
                    continue
            
            await asyncio.sleep(0.1)  # 短暂等待后重试
        
        return None
    
    async def wait_for_condition(
        self, 
        condition: Callable[[], bool], 
        timeout: Optional[int] = None,
        check_interval: float = 0.5
    ) -> bool:
        """等待条件满足
        
        Args:
            condition: 条件函数
            timeout: 超时时间（毫秒）
            check_interval: 检查间隔（秒）
        
        Returns:
            bool: 条件是否满足
        """
        timeout = timeout or self.default_timeout
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) * 1000 < timeout:
            try:
                if await condition() if asyncio.iscoroutinefunction(condition) else condition():
                    return True
            except Exception as e:
                logger.debug(f"条件检查出错: {str(e)}")
            
            await asyncio.sleep(check_interval)
        
        return False
    
    async def wait_for_page_load(self, timeout: Optional[int] = None) -> bool:
        """等待页面加载完成
        
        Args:
            timeout: 超时时间（毫秒）
        
        Returns:
            bool: 页面是否加载完成
        """
        timeout = timeout or self.default_timeout
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"等待页面加载超时: {str(e)}")
            return False
    
    async def wait_for_url_change(
        self, 
        expected_url_pattern: str = None, 
        timeout: Optional[int] = None
    ) -> bool:
        """等待URL变化
        
        Args:
            expected_url_pattern: 期望的URL模式
            timeout: 超时时间（毫秒）
        
        Returns:
            bool: URL是否按预期变化
        """
        timeout = timeout or self.default_timeout
        current_url = self.page.url
        
        try:
            if expected_url_pattern:
                await self.page.wait_for_url(expected_url_pattern, timeout=timeout)
            else:
                # 等待URL发生任何变化
                await self.wait_for_condition(
                    lambda: self.page.url != current_url,
                    timeout
                )
            return True
        except Exception as e:
            logger.debug(f"等待URL变化超时: {str(e)}")
            return False
    
    async def smart_scroll_and_wait(
        self, 
        selector: str, 
        timeout: Optional[int] = None
    ) -> Optional[Locator]:
        """智能滚动并等待元素出现
        
        Args:
            selector: CSS选择器
            timeout: 超时时间（毫秒）
        
        Returns:
            Optional[Locator]: 找到的元素
        """
        timeout = timeout or self.default_timeout
        start_time = asyncio.get_event_loop().time()
        
        # 首先尝试直接查找
        element = await self.wait_for_element(selector, timeout=1000)
        if element:
            return element
        
        # 如果找不到，尝试滚动查找
        scroll_steps = [0, 0.25, 0.5, 0.75, 1.0]  # 滚动到不同位置
        
        for ratio in scroll_steps:
            if (asyncio.get_event_loop().time() - start_time) * 1000 >= timeout:
                break
            
            # 滚动到指定位置
            await self.page.evaluate(f'''
                () => {{
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollTo(0, scrollHeight * {ratio});
                }}
            ''')
            
            await asyncio.sleep(0.5)  # 等待滚动完成
            
            # 再次尝试查找元素
            element = await self.wait_for_element(selector, timeout=2000)
            if element:
                return element
        
        return None 