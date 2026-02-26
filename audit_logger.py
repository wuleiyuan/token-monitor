#!/usr/bin/env python3
"""
API请求审计日志模块
企业版Token监控系统
"""

import logging
import json
from datetime import datetime
from typing import Optional
from fastapi import Request
import os

# 审计日志配置
AUDIT_LOG_FILE = os.getenv("AUDIT_LOG_FILE", "api_audit.log")
REQUEST_ID_HEADER = "X-Request-ID"


class AuditLogger:
    """API审计日志器"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        handler = logging.FileHandler(AUDIT_LOG_FILE, encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        ))
        self.logger.addHandler(handler)
        
        # 内存存储最近1000条审计记录
        self.recent_logs = []
        self.max_recent = 1000
    
    def log_request(self, request: Request, user: Optional[dict] = None, 
                    status_code: int = 200, duration_ms: float = 0):
        """记录API请求"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "user": user.get("username") if user else "anonymous",
            "request_id": request.headers.get(REQUEST_ID_HEADER, "none")
        }
        
        # 内存存储
        self.recent_logs.append(audit_entry)
        if len(self.recent_logs) > self.max_recent:
            self.recent_logs.pop(0)
        
        # 文件日志
        self.logger.info(json.dumps(audit_entry, ensure_ascii=False))
        
        return audit_entry
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """获取最近审计日志"""
        return self.recent_logs[-limit:]
    
    def get_stats(self) -> dict:
        """获取审计统计"""
        if not self.recent_logs:
            return {"total": 0}
        
        total = len(self.recent_logs)
        status_counts = {}
        path_counts = {}
        
        for log in self.recent_logs:
            status = log.get("status_code", 0)
            status_counts[status] = status_counts.get(status, 0) + 1
            
            path = log.get("path", "unknown")
            path_counts[path] = path_counts.get(path, 0) + 1
        
        return {
            "total": total,
            "status_distribution": status_counts,
            "top_paths": dict(sorted(path_counts.items(), 
                                   key=lambda x: x[1], reverse=True)[:10])
        }


# 全局审计日志实例
audit_logger = AuditLogger()


def generate_request_id():
    """生成请求ID"""
    import uuid
    return str(uuid.uuid4())[:8]
