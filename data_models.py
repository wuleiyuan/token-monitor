#!/usr/bin/env python3
"""
数据模型模块
统一数据结构，确保前后端一致性
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class TokenUsage:
    """Token使用记录数据模型"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    model_name: str = ""
    model_type: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    response_time: Optional[int] = None
    status: str = "success"
    api_provider: Optional[str] = None
    request_type: Optional[str] = None
    user_id: str = "default"
    session_id: Optional[str] = None
    agent_name: Optional[str] = None
    category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，保持向后兼容"""
        result = asdict(self)
        
        # 时间戳格式化
        if isinstance(result['timestamp'], datetime):
            result['timestamp'] = result['timestamp'].isoformat()
        
        # 前端兼容字段映射
        frontend_mapping = {
            'model': result['model_name'],
            'tokens': result['tokens_used'],
            'responseTime': result['response_time'],
            'apiProvider': result['api_provider'],
            'requestType': result['request_type']
        }
        
        # 只添加不存在的字段，避免覆盖
        for key, value in frontend_mapping.items():
            if key not in result:
                result[key] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenUsage':
        """从字典创建实例"""
        # 处理时间戳
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                timestamp = datetime.now()
        elif timestamp is None:
            timestamp = datetime.now()
        
        # 处理前端字段映射
        model_name = data.get('model_name') or data.get('model', '')
        tokens_used = data.get('tokens_used') or data.get('tokens', 0)
        response_time = data.get('response_time') or data.get('responseTime')
        api_provider = data.get('api_provider') or data.get('apiProvider')
        request_type = data.get('request_type') or data.get('requestType')
        
        return cls(
            id=data.get('id'),
            timestamp=timestamp,
            model_name=model_name,
            model_type=data.get('model_type', ''),
            tokens_used=tokens_used,
            cost=float(data.get('cost', 0.0)),
            response_time=response_time,
            status=data.get('status', 'success'),
            api_provider=api_provider,
            request_type=request_type,
            user_id=data.get('user_id', 'default'),
            session_id=data.get('session_id'),
            agent_name=data.get('agent_name'),
            category=data.get('category')
        )


@dataclass
class ModelInfo:
    """模型信息数据模型"""
    name: str
    type: str  # 'paid' or 'free'
    provider: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UsageStats:
    """使用统计数据模型"""
    total_tokens: int = 0
    total_cost: float = 0.0
    total_calls: int = 0
    avg_tokens: int = 0
    tokens_change: float = 0.0
    cost_change: float = 0.0
    calls_change: float = 0.0
    avg_tokens_change: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataValidationError(Exception):
    """数据验证错误"""
    pass


class TokenUsageValidator:
    """Token使用数据验证器"""
    
    @staticmethod
    def validate_token_usage(data: Dict[str, Any]) -> TokenUsage:
        """验证并创建TokenUsage实例"""
        try:
            # 必需字段检查
            required_fields = ['model_name', 'model_type', 'tokens_used', 'cost']
            for field in required_fields:
                if field not in data and field not in ['model', 'tokens']:
                    raise DataValidationError(f"Missing required field: {field}")
            
            # 数据类型和范围验证
            tokens_used = data.get('tokens_used') or data.get('tokens', 0)
            if not isinstance(tokens_used, int) or tokens_used < 0:
                raise DataValidationError("tokens_used must be a non-negative integer")
            
            cost = data.get('cost', 0.0)
            if not isinstance(cost, (int, float)) or cost < 0:
                raise DataValidationError("cost must be a non-negative number")
            
            model_type = data.get('model_type', '')
            if model_type not in ['paid', 'free']:
                raise DataValidationError("model_type must be 'paid' or 'free'")
            
            status = data.get('status', 'success')
            if status not in ['success', 'error', 'timeout']:
                raise DataValidationError("status must be valid status value")
            
            return TokenUsage.from_dict(data)
            
        except Exception as e:
            if isinstance(e, DataValidationError):
                raise
            raise DataValidationError(f"Data validation failed: {e}")


class DatabaseManager:
    """数据库管理器 - 统一数据库操作"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        import sqlite3
        import os
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    model_name TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    cost REAL NOT NULL,
                    response_time INTEGER,
                    status TEXT DEFAULT 'success',
                    api_provider TEXT,
                    request_type TEXT,
                    user_id TEXT DEFAULT 'default',
                    session_id TEXT,
                    agent_name TEXT,
                    category TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE,
                    total_tokens INTEGER,
                    total_cost REAL,
                    total_calls INTEGER,
                    free_tokens INTEGER,
                    paid_tokens INTEGER
                )
            ''')
            
            # 创建性能优化索引
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp 
                ON token_usage(timestamp DESC)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_token_usage_model_type 
                ON token_usage(model_type)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp_model 
                ON token_usage(timestamp DESC, model_type)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_token_usage_provider_model 
                ON token_usage(api_provider, model_name)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_token_usage_user_session 
                ON token_usage(user_id, session_id)
            ''')
            
            conn.commit()
    
    def insert_token_usage(self, token_usage: TokenUsage) -> bool:
        """插入Token使用记录"""
        try:
            import sqlite3
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO token_usage 
                    (model_name, model_type, tokens_used, cost, response_time, status, 
                     api_provider, request_type, user_id, session_id, agent_name, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    token_usage.model_name,
                    token_usage.model_type,
                    token_usage.tokens_used,
                    token_usage.cost,
                    token_usage.response_time,
                    token_usage.status,
                    token_usage.api_provider,
                    token_usage.request_type,
                    token_usage.user_id,
                    token_usage.session_id,
                    token_usage.agent_name,
                    token_usage.category
                ))
                conn.commit()
            return True
        except Exception as e:
            import logging
            logging.error(f"插入数据失败: {e}")
            return False
    
    def get_usage_data(self, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> list[TokenUsage]:
        """获取使用数据"""
        try:
            import sqlite3
            
            where_conditions = []
            params = []
            
            if filters is not None:
                # 时间范围过滤
                time_range = filters.get('timeRange', 'week')
                if time_range == 'day':
                    where_conditions.append("DATE(timestamp) = DATE('now')")
                elif time_range == 'week':
                    where_conditions.append("DATE(timestamp) >= DATE('now', '-7 days')")
                elif time_range == 'month':
                    where_conditions.append("DATE(timestamp) >= DATE('now', '-30 days')")
                elif time_range == 'year':
                    where_conditions.append("DATE(timestamp) >= DATE('now', '-365 days')")
                
                # 模型类型过滤
                model_type = filters.get('modelType')
                if model_type and model_type != 'all':
                    where_conditions.append("model_type = ?")
                    params.append(model_type)
                
                # 具体模型过滤
                specific_model = filters.get('specificModel')
                if specific_model and specific_model != 'all':
                    where_conditions.append("model_name LIKE ?")
                    params.append(f"%{specific_model}%")
                
                # 日期范围过滤
                start_date = filters.get('startDate')
                if start_date:
                    where_conditions.append("DATE(timestamp) >= ?")
                    params.append(start_date)
                
                end_date = filters.get('endDate')
                if end_date:
                    where_conditions.append("DATE(timestamp) <= ?")
                    params.append(end_date)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = '''
                    SELECT * FROM token_usage 
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ?
                '''
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # 转换为TokenUsage对象
                columns = [description[0] for description in cursor.description]
                results = []
                
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    results.append(TokenUsage.from_dict(row_dict))
                
                return results
                
        except Exception as e:
            import logging
            logging.error(f"查询数据失败: {e}")
            return []