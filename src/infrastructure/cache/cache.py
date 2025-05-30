"""
缓存管理模块
实现内存缓存功能，支持TTL和缓存清理
"""
import asyncio
import time
from typing import Any, Dict, Optional, Union
from src.core.logging.logger import logger

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        logger.info("缓存管理器初始化")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            Any: 缓存值，如果不存在或已过期则返回None
        """
        if key not in self.cache:
            return None
            
        cache_item = self.cache[key]
        if 'expire_at' in cache_item and cache_item['expire_at'] < time.time():
            # 缓存已过期，删除并返回None
            del self.cache[key]
            return None
            
        return cache_item['value']
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示永不过期
        """
        cache_item = {'value': value}
        
        if ttl is not None:
            cache_item['expire_at'] = time.time() + ttl
            
        self.cache[key] = cache_item
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 删除成功返回True，键不存在返回False
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    async def cleanup_expired(self) -> int:
        """
        清理所有过期缓存
        
        Returns:
            int: 清理的缓存项数量
        """
        now = time.time()
        expired_keys = [
            key for key, item in self.cache.items()
            if 'expire_at' in item and item['expire_at'] < now
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            logger.info(f"已清理 {len(expired_keys)} 个过期缓存项")
            
        return len(expired_keys)

# 全局缓存管理器实例
cache_manager = CacheManager() 