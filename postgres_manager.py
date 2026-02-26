#!/usr/bin/env python3
"""
PostgreSQL数据库管理器
支持连接池、异步操作、高并发处理
"""

import asyncio
import asyncpg
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass

from config_manager import config
from data_models import TokenUsage
from error_handling import DatabaseError


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_min_size: int = 5
    pool_max_size: int = 20
    command_timeout: int = 60


class PostgreSQLManager:
    """PostgreSQL数据库管理器 - 企业级数据库解决方案"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """初始化连接池"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                min_size=self.config.pool_min_size,
                max_size=self.config.pool_max_size,
                command_timeout=self.config.command_timeout,
                ssl='disable'
            )
            
            # 创建必要的表
            await self._create_tables()
            
            logging.info("PostgreSQL连接池初始化成功")
            
        except Exception as e:
            logging.error(f"数据库连接池初始化失败: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    async def _create_tables(self):
        """创建数据库表"""
        async with self.pool.acquire() as conn:
            # 创建token_usage表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS token_usage (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    model_name VARCHAR(255) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    cost DECIMAL(10,4) NOT NULL,
                    response_time INTEGER,
                    status VARCHAR(50) DEFAULT 'success',
                    api_provider VARCHAR(100),
                    request_type VARCHAR(100),
                    user_id VARCHAR(100) DEFAULT 'default',
                    session_id VARCHAR(255),
                    agent_name VARCHAR(255),
                    category VARCHAR(100)
                )
            ''')
            
            # 创建daily_summary表
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_summary (
                    id SERIAL PRIMARY KEY,
                    date DATE UNIQUE,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost DECIMAL(12,4) DEFAULT 0.0000,
                    total_calls INTEGER DEFAULT 0,
                    free_tokens INTEGER DEFAULT 0,
                    paid_tokens INTEGER DEFAULT 0
                )
            ''')
            
            # 创建索引
            await self._create_indexes(conn)
            
            logging.info("数据库表创建完成")
    
    async def _create_indexes(self, conn):
        """创建性能索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp ON token_usage(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_token_usage_model_type ON token_usage(model_type)",
            "CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp_model ON token_usage(timestamp DESC, model_type)",
            "CREATE INDEX IF NOT EXISTS idx_token_usage_provider_model ON token_usage(api_provider, model_name)",
            "CREATE INDEX IF NOT EXISTS idx_token_usage_user_session ON token_usage(user_id, session_id)"
        ]
        
        for index_sql in indexes:
            await conn.execute(index_sql)
        
        logging.info("数据库索引创建完成")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接的上下文管理器"""
        async with self._lock:
            if self.pool is None:
                await self.initialize()
            
            conn = await self.pool.acquire()
            try:
                yield conn
            finally:
                await self.pool.release(conn)
    
    async def insert_token_usage(self, token_usage: TokenUsage) -> bool:
        """异步插入Token使用记录"""
        try:
            async with self.get_connection() as conn:
                await conn.execute('''
                    INSERT INTO token_usage 
                    (model_name, model_type, tokens_used, cost, response_time, status, 
                     api_provider, request_type, user_id, session_id, agent_name, category)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ''', (
                    token_usage.model_name,
                    token_usage.model_type,
                    token_usage.tokens_used,
                    float(token_usage.cost),
                    token_usage.response_time,
                    token_usage.status,
                    token_usage.api_provider,
                    token_usage.request_type,
                    token_usage.user_id,
                    token_usage.session_id,
                    token_usage.agent_name,
                    token_usage.category
                ))
            
            logging.info(f"成功插入Token使用记录: {token_usage.model_name}")
            return True
            
        except Exception as e:
            logging.error(f"插入Token使用记录失败: {e}")
            return False
    
    async def get_usage_data(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[TokenUsage]:
        """异步获取使用数据"""
        try:
            where_conditions = []
            params = []
            param_count = 1
            
            if filters is not None:
                # 时间范围过滤
                time_range = filters.get('timeRange', 'week')
                if time_range == 'day':
                    where_conditions.append(f"DATE(timestamp) = CURRENT_DATE")
                elif time_range == 'week':
                    where_conditions.append(f"timestamp >= CURRENT_DATE - INTERVAL '7 days'")
                elif time_range == 'month':
                    where_conditions.append(f"timestamp >= CURRENT_DATE - INTERVAL '30 days'")
                elif time_range == 'year':
                    where_conditions.append(f"timestamp >= CURRENT_DATE - INTERVAL '365 days'")
                
                # 模型类型过滤
                model_type = filters.get('modelType')
                if model_type and model_type != 'all':
                    where_conditions.append(f"model_type = ${param_count}")
                    params.append(model_type)
                    param_count += 1
                
                # 具体模型过滤
                specific_model = filters.get('specificModel')
                if specific_model and specific_model != 'all':
                    where_conditions.append(f"model_name LIKE ${param_count}")
                    params.append(f"%{specific_model}%")
                    param_count += 1
                
                # 日期范围过滤
                start_date = filters.get('startDate')
                if start_date:
                    where_conditions.append(f"DATE(timestamp) >= ${param_count}")
                    params.append(start_date)
                    param_count += 1
                
                end_date = filters.get('endDate')
                if end_date:
                    where_conditions.append(f"DATE(timestamp) <= ${param_count}")
                    params.append(end_date)
                    param_count += 1
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            params.append(limit)
            
            async with self.get_connection() as conn:
                rows = await conn.fetch(f'''
                    SELECT * FROM token_usage 
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ${param_count}
                ''', *params)
                
                # 转换为TokenUsage对象
                results = []
                for row in rows:
                    row_dict = dict(row)
                    results.append(TokenUsage.from_dict(row_dict))
                
                logging.info(f"获取到 {len(results)} 条记录")
                return results
                
        except Exception as e:
            logging.error(f"查询使用数据失败: {e}")
            raise DatabaseError(f"Failed to get usage data: {e}")
    
    async def get_stats(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """异步获取统计数据"""
        try:
            where_conditions = []
            params = []
            param_count = 1
            
            if filters is not None:
                time_range = filters.get('timeRange', 'week')
                if time_range == 'day':
                    where_conditions.append(f"DATE(timestamp) = CURRENT_DATE")
                elif time_range == 'week':
                    where_conditions.append(f"timestamp >= CURRENT_DATE - INTERVAL '7 days'")
                elif time_range == 'month':
                    where_conditions.append(f"timestamp >= CURRENT_DATE - INTERVAL '30 days'")
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            async with self.get_connection() as conn:
                row = await conn.fetchrow(f'''
                    SELECT 
                        COUNT(*) as total_calls,
                        SUM(tokens_used) as total_tokens,
                        SUM(cost) as total_cost,
                        COUNT(CASE WHEN model_type = 'paid' THEN 1 END) as paid_calls,
                        COUNT(CASE WHEN model_type = 'free' THEN 1 END) as free_calls,
                        SUM(CASE WHEN model_type = 'paid' THEN tokens_used ELSE 0 END) as paid_tokens,
                        SUM(CASE WHEN model_type = 'free' THEN tokens_used ELSE 0 END) as free_tokens
                    FROM token_usage 
                    WHERE {where_clause}
                ''', *params)
                
                if row:
                    stats = {
                        'total_calls': int(row['total_calls']),
                        'total_tokens': int(row['total_tokens'] or 0),
                        'total_cost': float(row['total_cost'] or 0),
                        'paid_calls': int(row['paid_calls'] or 0),
                        'free_calls': int(row['free_calls'] or 0),
                        'paid_tokens': int(row['paid_tokens'] or 0),
                        'free_tokens': int(row['free_tokens'] or 0)
                    }
                else:
                    stats = {
                        'total_calls': 0,
                        'total_tokens': 0,
                        'total_cost': 0.0,
                        'paid_calls': 0,
                        'free_calls': 0,
                        'paid_tokens': 0,
                        'free_tokens': 0
                    }
                
                logging.info(f"统计数据: {stats}")
                return stats
                
        except Exception as e:
            logging.error(f"获取统计数据失败: {e}")
            raise DatabaseError(f"Failed to get stats: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        try:
            async with self.get_connection() as conn:
                # 测试连接
                result = await conn.fetchval("SELECT 1 as health_check")
                
                # 获取连接池状态
                pool_size = self.pool.get_size()
                pool_free = self.pool.get_idle_size()
                
                return {
                    "status": "healthy",
                    "database": "postgresql",
                    "pool_size": pool_size,
                    "pool_free": pool_free,
                    "timestamp": asyncio.get_event_loop().time()
                }
                
        except Exception as e:
            logging.error(f"数据库健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def close(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            logging.info("PostgreSQL连接池已关闭")


def create_postgres_manager() -> PostgreSQLManager:
    """从配置创建PostgreSQL管理器"""
    return PostgreSQLManager(DatabaseConfig(
        host=config.get('database', 'host', 'localhost'),
        port=config.get_int('database', 'port', 5432),
        database=config.get('database', 'name', 'token_monitor'),
        username=config.get('database', 'username', 'postgres'),
        password=config.get('database', 'password', ''),
        pool_min_size=config.get_int('database', 'pool_min_size', 5),
        pool_max_size=config.get_int('database', 'pool_max_size', 20)
    ))