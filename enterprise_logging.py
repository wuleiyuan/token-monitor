#!/usr/bin/env python3
"""
企业级日志和监控系统
提供结构化日志、指标收集、告警通知等功能
"""

import logging
import json
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from functools import wraps
import asyncio
import psutil
from dataclasses import dataclass, asdict


@dataclass
class LogEntry:
    """结构化日志条目"""
    timestamp: str
    level: str
    message: str
    module: str
    function: str
    line_number: Optional[int]
    exception: Optional[str]
    extra_data: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    network_io: Dict[str, int]
    active_connections: int
    response_time: Optional[float] = None
    endpoint: Optional[str] = None


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: str
    threshold: float
    severity: str
    enabled: bool


class EnterpriseLogger:
    """企业级日志系统"""
    
    def __init__(self, name: str = "token_monitor"):
        self.name = name
        self.logger = self._setup_logger()
        self.performance_metrics = []
        self.alert_rules = self._setup_alert_rules()
        self.error_counts = {}
        
    def _setup_logger(self) -> logging.Logger:
        """设置结构化日志器"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        logger.handlers.clear()
        
        # 控制台处理器
        console_handler = StructuredConsoleHandler()
        console_handler.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = StructuredFileHandler(
            filename=f"{self.name}.log",
            max_bytes=50*1024*1024,  # 50MB
            backup_count=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 错误文件处理器
        error_handler = StructuredFileHandler(
            filename=f"{self.name}_errors.log",
            max_bytes=10*1024*1024,  # 10MB
            backup_count=3
        )
        error_handler.setLevel(logging.ERROR)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        
        return logger
    
    def _setup_alert_rules(self) -> List[AlertRule]:
        """设置告警规则"""
        return [
            AlertRule("高CPU使用", "cpu_percent", 80.0, "warning", True),
            AlertRule("高内存使用", "memory_percent", 85.0, "warning", True),
            AlertRule("高磁盘使用", "disk_usage", 90.0, "critical", True),
            AlertRule("错误率过高", "error_rate", 5.0, "warning", True),
            AlertRule("响应时间过长", "response_time", 2000.0, "warning", True)
        ]
    
    def log_structured(self, level: str, message: str, **kwargs):
        """记录结构化日志"""
        # 获取调用栈信息
        frame = sys._getframe(1)
        module = frame.f_globals.get('__name__', 'unknown')
        function = frame.f_code.co_name
        line_number = frame.f_lineno if hasattr(frame, 'f_lineno') else None
        
        log_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            exception=kwargs.get('exception'),
            extra_data=kwargs.get('extra_data')
        )
        
        # 记录到结构化日志
        if level.upper() == 'ERROR':
            self.logger.error(json.dumps(asdict(log_entry), default=str), exc_info=kwargs.get('exc_info'))
        elif level.upper() == 'WARNING':
            self.logger.warning(json.dumps(asdict(log_entry), default=str))
        elif level.upper() == 'INFO':
            self.logger.info(json.dumps(asdict(log_entry), default=str))
        else:
            self.logger.debug(json.dumps(asdict(log_entry), default=str))
        
        # 更新错误计数
        if level.upper() == 'ERROR':
            self._increment_error_count(module, function)
    
    def _increment_error_count(self, module: str, function: str):
        """增加错误计数"""
        key = f"{module}.{function}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
    
    def collect_performance_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        try:
            # CPU和内存使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 网络IO
            net_io = psutil.net_io_counters()
            
            # 当前时间
            timestamp = datetime.now().isoformat()
            
            metrics = PerformanceMetrics(
                timestamp=timestamp,
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage=disk.percent,
                network_io={
                    'bytes_sent': getattr(net_io, 'bytes_sent', 0),
                    'bytes_recv': getattr(net_io, 'bytes_recv', 0)
                },
                active_connections=len(self.performance_metrics) if self.performance_metrics else 0
            )
            
            self.performance_metrics.append(metrics)
            
            # 保留最近1000个指标
            if len(self.performance_metrics) > 1000:
                self.performance_metrics = self.performance_metrics[-1000:]
            
            # 检查告警
            self._check_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            self.log_structured('ERROR', f"性能指标收集失败: {e}", extra_data={'error': str(e)})
            # 返回默认指标
            return PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage=0.0,
                network_io={'bytes_sent': 0, 'bytes_recv': 0}
            )
    
    def _check_alerts(self, metrics: PerformanceMetrics):
        """检查告警条件"""
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
                
            value = getattr(metrics, rule.condition, 0.0)
            if value > rule.threshold:
                self._send_alert(rule, metrics, value)
    
    def _send_alert(self, rule: AlertRule, metrics: PerformanceMetrics, value: float):
        """发送告警"""
        alert_data = {
            'timestamp': metrics.timestamp,
            'rule_name': rule.name,
            'condition': rule.condition,
            'current_value': value,
            'threshold': rule.threshold,
            'severity': rule.severity,
            'metrics': asdict(metrics)
        }
        
        self.log_structured('WARNING', f"告警触发: {rule.name}", extra_data=alert_data)
        
        # 这里可以扩展为发送邮件、Slack通知等
        # self._send_notification(alert_data)
    
    def get_error_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """获取错误摘要"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_errors = {}
        total_errors = 0
        
        for key, count in self.error_counts.items():
            if count > 0:
                recent_errors[key] = count
                total_errors += count
        
        return {
            'time_window_minutes': minutes,
            'total_errors': total_errors,
            'error_breakdown': recent_errors,
            'top_error_modules': self._get_top_errors(recent_errors, 5)
        }
    
    def _get_top_errors(self, errors: Dict[str, int], limit: int) -> List[Dict[str, Any]]:
        """获取最多的错误"""
        sorted_errors = sorted(errors.items(), key=lambda x: x[1], reverse=True)
        return [{'module_function': k, 'count': v} for k, v in sorted_errors[:limit]]
    
    def get_performance_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_metrics:
            return {'status': 'no_data'}
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.performance_metrics 
            if datetime.fromisoformat(m.timestamp) > cutoff_time
        ]
        
        if not recent_metrics:
            return {'status': 'no_recent_data'}
        
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        response_times = [m.response_time for m in recent_metrics if m.response_time]
        
        return {
            'time_window_minutes': minutes,
            'sample_count': len(recent_metrics),
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'response_time': {
                'avg': sum(response_times) / len(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0,
                'min': min(response_times) if response_times else 0
            }
        }
    
    def export_logs(self, output_file: str, hours: int = 24):
        """导出日志"""
        try:
            log_file = Path(f"{self.name}.log")
            if not log_file.exists():
                return {'status': 'no_log_file'}
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            exported_entries = []
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(log_entry['timestamp'])
                        if entry_time > cutoff_time:
                            exported_entries.append(log_entry)
                    except json.JSONDecodeError:
                        continue
            
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(exported_entries, f, indent=2, ensure_ascii=False)
            
            return {
                'status': 'success',
                'exported_count': len(exported_entries),
                'output_file': str(output_path)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


class StructuredConsoleHandler(logging.Handler):
    """结构化控制台日志处理器"""
    
    def emit(self, record):
        """输出格式化的日志"""
        try:
            log_data = json.loads(record.getMessage())
            level_color = {
                'DEBUG': '\033[36m',      # Cyan
                'INFO': '\033[32m',       # Green
                'WARNING': '\033[33m',    # Yellow
                'ERROR': '\033[31m',      # Red
                'CRITICAL': '\033[35m'    # Magenta
            }.get(record.levelname, '\033[0m')
            
            reset_color = '\033[0m'
            
            print(f"{level_color}{record.levelname}{reset_color} "
                  f"{log_data['timestamp']} "
                  f"[{log_data.get('module', 'unknown')}] "
                  f"{log_data['message']}")
                  
            if log_data.get('exception'):
                print(f"Exception: {log_data['exception']}")
                
        except json.JSONDecodeError:
            print(f"{record.levelname}: {record.getMessage()}")


class StructuredFileHandler(logging.Handler):
    """结构化文件日志处理器"""
    
    def __init__(self, filename: str, max_bytes: int = 10*1024*1024, backup_count: int = 5):
        super().__init__()
        self.filename = filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # 创建日志目录
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        # 设置文件轮转
        from logging.handlers import RotatingFileHandler
        self.handler = RotatingFileHandler(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
    
    def emit(self, record):
        """写入格式化的日志"""
        try:
            log_data = json.loads(record.getMessage())
            
            # 添加格式化的时间戳
            timestamp = datetime.fromisoformat(log_data['timestamp']).strftime(
                '%Y-%m-%d %H:%M:%S'
            )
            
            formatted_message = (
                f"{timestamp} [{record.levelname}] "
                f"[{log_data.get('module', 'unknown')}] "
                f"{log_data['message']}\n"
            )
            
            if log_data.get('exception'):
                formatted_message += f"Exception: {log_data['exception']}\n"
            
            self.handler.emit(logging.LogRecord(
                name=record.name,
                level=record.levelno,
                pathname=record.pathname,
                lineno=record.lineno,
                msg=formatted_message.strip(),
                args=(),
                exc_info=None
            ))
            
        except (json.JSONDecodeError, Exception) as e:
            self.handler.emit(record)


def monitor_endpoint_performance(func):
    """监控端点性能的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            # 记录性能指标
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            if hasattr(wrapper, 'enterprise_logger'):
                wrapper.enterprise_logger.collect_performance_metrics()
                if wrapper.enterprise_logger.performance_metrics:
                    wrapper.enterprise_logger.performance_metrics[-1].response_time = response_time
                    wrapper.enterprise_logger.performance_metrics[-1].endpoint = func.__name__
            
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            if hasattr(wrapper, 'enterprise_logger'):
                wrapper.enterprise_logger.log_structured(
                    'ERROR', 
                    f"端点 {func.__name__} 执行失败: {e}",
                    exception=str(e),
                    extra_data={
                        'function': func.__name__,
                        'response_time': response_time,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                )
            
            raise
    
    return wrapper


# 全局日志实例
enterprise_logger = EnterpriseLogger()