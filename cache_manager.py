#!/usr/bin/env python3
"""
Redis缓存管理器
提供高性能缓存支持，减少数据库查询压力
"""

import json
import asyncio
import redis.asyncio as redis
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from functools import wraps

from config_manager import config
from error_handling import DatabaseError


class CacheManager:
    """Redis缓存管理器 - 企业级缓存解决方案"""
    
    def __init__(self):
        self.redis = None
        self.default_ttl = 300
    
    async def initialize(self):
        """初始化Redis连接"""
        try:
            host = config.get('cache', 'redis_host', 'localhost')
            port = config.get_int('cache', 'redis_port', 6379)
            db = config.get_int('cache', 'redis_db', 0)
            password = config.get('cache', 'redis_password', '')
            
            self.redis = redis.from_url(
                f"redis://:{password}@{host}:{port}/{db}" if password else f"redis://{host}:{port}/{db}",
                encoding="utf-8",
                decode_responses=True
            )
            
            await self.redis.ping()
            
            logging.info("Redis缓存初始化成功")
            
        except Exception as e:
            logging.error(f"Redis缓存初始化失败: {e}")
            raise DatabaseError(f"Failed to initialize cache: {e}")
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.aclose()
            logging.info("Redis缓存已关闭")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            if not self.redis:
                return None
                
            value = await self.redis.get(key)
            if value:
                logging.debug(f"缓存命中: {key}")
                return json.loads(value)
            return None
            
        except Exception as e:
            logging.error(f"缓存获取失败 {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            if not self.redis:
                return False
                
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            
            await self.redis.setex(key, ttl, serialized_value)
            logging.debug(f"缓存设置: {key}, TTL: {ttl}s")
            return True
            
        except Exception as e:
            logging.error(f"缓存设置失败 {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            if not self.redis:
                return False
                
            await self.redis.delete(key)
            logging.debug(f"缓存删除: {key}")
            return True
            
        except Exception as e:
            logging.error(f"缓存删除失败 {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            if not self.redis:
                return False
                
            result = await self.redis.exists(key)
            return bool(result)
            
        except Exception as e:
            logging.error(f"缓存检查失败 {key}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取Redis统计信息"""
        try:
            if not self.redis:
                return {"status": "disconnected"}
                
            info = await self.redis.info()
            
            return {
                "status": "connected",
                "used_memory": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 'N/A'),
                "total_commands_processed": info.get('total_commands_processed', 'N/A'),
                "keyspace_hits": info.get('keyspace_hits', 'N/A'),
                "keyspace_misses": info.get('keyspace_misses', 'N/A')
            }
            
        except Exception as e:
            logging.error(f"获取Redis统计失败: {e}")
            return {"status": "error", "error": str(e)}


# 缓存装饰器
def cache_result(ttl: int = 300, key_prefix: str = ""):
    """缓存函数结果的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 尝试从缓存获取
            cache_manager = getattr(wrapper, '_cache_manager', None)
            if cache_manager:
                cached_result = await cache_manager.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # 执行原函数
            try:
                result = await func(*args, **kwargs)
                
                # 缓存结果
                if cache_manager:
                    await cache_manager.set(cache_key, result, ttl)
                
                return result
                
            except Exception as e:
                logging.error(f"缓存函数执行失败 {func.__name__}: {e}")
                raise
        
        # 设置缓存管理器的引用方法
        def set_cache_manager(cm):
            wrapper._cache_manager = cm
        
        wrapper.set_cache_manager = set_cache_manager
        return wrapper
    return decorator


class UsageDataCache:
    """使用数据专用缓存管理"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.usage_data_ttl = 300  # 5分钟
        self.stats_ttl = 60     # 1分钟
        self.models_ttl = 3600   # 1小时
    
    def _get_usage_key(self, filters: Dict[str, Any], limit: int) -> str:
        """生成使用数据缓存键"""
        filter_str = json.dumps(sorted(filters.items()))
        return f"usage_data:{hash(filter_str)}:{limit}"
    
    def _get_stats_key(self, filters: Dict[str, Any]) -> str:
        """生成统计数据缓存键"""
        filter_str = json.dumps(sorted(filters.items()))
        return f"stats:{hash(filter_str)}"
    
    def _get_models_key(self) -> str:
        """生成模型列表缓存键"""
        return "models:list"
    
    async def get_usage_data(self, filters: Dict[str, Any], limit: int) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的使用数据"""
        cache_key = self._get_usage_key(filters, limit)
        return await self.cache_manager.get(cache_key)
    
    async def set_usage_data(self, filters: Dict[str, Any], limit: int, data: List[Dict[str, Any]]) -> bool:
        """缓存使用数据"""
        cache_key = self._get_usage_key(filters, limit)
        return await self.cache_manager.set(cache_key, data, self.usage_data_ttl)
    
    async def get_stats(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取缓存的统计数据"""
        cache_key = self._get_stats_key(filters)
        return await self.cache_manager.get(cache_key)
    
    async def set_stats(self, filters: Dict[str, Any], stats: Dict[str, Any]) -> bool:
        """缓存统计数据"""
        cache_key = self._get_stats_key(filters)
        return await self.cache_manager.set(cache_key, stats, self.stats_ttl)
    
    async def get_models(self) -> Optional[Dict[str, List[str]]]:
        """获取缓存的模型列表"""
        cache_key = self._get_models_key()
        return await self.cache_manager.get(cache_key)
    
    async def set_models(self, models: Dict[str, List[str]]) -> bool:
        """缓存模型列表"""
        cache_key = self._get_models_key()
        return await self.cache_manager.set(cache_key, models, self.models_ttl)
    
    async def invalidate_usage_cache(self):
        """失效使用数据相关的缓存"""
        patterns = [
            "usage_data:*",
            "stats:*"
        ]
        
        for pattern in patterns:
            try:
                keys = await self.cache_manager.redis.keys(pattern)
                if keys:
                    await self.cache_manager.redis.delete(keys)
                    logging.info(f"失效缓存模式: {pattern}, 删除了 {len(keys)} 个键")
            except Exception as e:
                logging.warning(f"失效缓存失败: {e}")


def create_cache_manager() -> CacheManager:
    """创建缓存管理器实例"""
    return CacheManager()