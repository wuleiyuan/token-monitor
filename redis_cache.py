#!/usr/bin/env python3
"""
Redis缓存模块
企业版Token监控系统
"""

import json
import os
from typing import Optional, Any
import redis
from datetime import timedelta

# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# 缓存时间配置（秒）
CACHE_TTL = {
    "usage_data": 300,      # 5分钟
    "stats": 60,            # 1分钟
    "models": 3600,         # 1小时
    "health": 30,           # 30秒
}


class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.enabled = False
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        try:
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            self.client.ping()
            self.enabled = True
            print("✅ Redis缓存已启用")
        except redis.ConnectionError:
            print("⚠️ Redis连接失败，使用内存缓存")
            self.client = None
            self._memory_cache = {}
        except Exception as e:
            print(f"⚠️ Redis初始化失败: {e}")
            self.client = None
            self._memory_cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.enabled or self.client is None:
            return self._memory_cache.get(key)
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception:
            pass
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """设置缓存"""
        if not self.enabled or self.client is None:
            self._memory_cache[key] = value
            return True
        
        try:
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.enabled or self.client is None:
            self._memory_cache.pop(key, None)
            return True
        
        try:
            self.client.delete(key)
            return True
        except Exception:
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """清除匹配的缓存"""
        if not self.enabled or self.client is None:
            keys = [k for k in self._memory_cache if k.startswith(pattern.replace("*", ""))]
            for k in keys:
                del self._memory_cache[k]
            return len(keys)
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
        except Exception:
            pass
        return 0
    
    def get_stats(self) -> dict:
        """获取缓存状态"""
        if not self.enabled or self.client is None:
            return {"enabled": False, "type": "memory", "keys": len(self._memory_cache)}
        
        try:
            info = self.client.info("stats")
            return {
                "enabled": True,
                "type": "redis",
                "keys": len(self.client.keys("*")),
                "memory": info.get("used_memory_human", "N/A"),
                "connections": info.get("connected_clients", 0)
            }
        except Exception:
            return {"enabled": False, "error": "cannot get stats"}


# 全局缓存实例
cache_manager = CacheManager()
