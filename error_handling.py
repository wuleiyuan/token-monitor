#!/usr/bin/env python3
"""
错误处理和日志系统
统一错误分类和日志管理
"""

import logging
import traceback
import functools
from typing import Callable, Any, Optional
from datetime import datetime


class TokenMonitorError(Exception):
    """Token监控系统基础异常类"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()


class DatabaseError(TokenMonitorError):
    """数据库相关错误"""
    pass


class ConfigError(TokenMonitorError):
    """配置相关错误"""
    pass


class APIError(TokenMonitorError):
    """API相关错误"""
    pass


class ValidationError(TokenMonitorError):
    """数据验证错误"""
    pass


class NetworkError(TokenMonitorError):
    """网络相关错误"""
    pass


class AuthenticationError(TokenMonitorError):
    """认证相关错误"""
    pass


class RateLimitError(TokenMonitorError):
    """频率限制错误"""
    pass


class LoggerManager:
    """日志管理器"""
    
    def __init__(self, name: str = "token_monitor", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self._setup_logger(level)
    
    def _setup_logger(self, level: str):
        """设置日志配置"""
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        try:
            from pathlib import Path
            from config_manager import config
            
            log_file = config.log_file
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            
            # 文件轮转
            max_size = config.get_int('logging', 'max_file_size_mb', 10) * 1024 * 1024
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            self.logger.warning(f"无法设置文件日志: {e}")
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        """错误日志"""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, exception: Exception = None, **kwargs):
        """严重错误日志"""
        if exception:
            self.logger.critical(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
        else:
            self.logger.critical(message, extra=kwargs)


# 全局日志实例
logger = LoggerManager()


def error_handler(error_type: type = None, default_return: Any = None, log_error: bool = True):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 确定错误类型
                if error_type and isinstance(e, error_type):
                    classified_error = e
                elif isinstance(e, TokenMonitorError):
                    classified_error = e
                elif "database" in str(e).lower() or "sqlite" in str(e).lower():
                    classified_error = DatabaseError(str(e))
                elif "network" in str(e).lower() or "connection" in str(e).lower():
                    classified_error = NetworkError(str(e))
                elif "config" in str(e).lower():
                    classified_error = ConfigError(str(e))
                else:
                    classified_error = TokenMonitorError(str(e))
                
                # 记录错误
                if log_error:
                    logger.error(
                        f"函数 {func.__name__} 执行失败",
                        exception=classified_error,
                        function=func.__name__,
                        args=str(args)[:200],  # 限制日志长度
                        kwargs=str(kwargs)[:200]
                    )
                
                # 返回默认值或重新抛出
                if default_return is not None:
                    return default_return
                else:
                    raise classified_error
        
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default_return: Any = None, **kwargs) -> Any:
    """安全执行函数"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"安全执行失败: {func.__name__}", exception=e)
        return default_return


class ErrorRecovery:
    """错误恢复管理器"""
    
    @staticmethod
    def retry(max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 2.0):
        """重试装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"第 {attempt + 1} 次尝试失败，{delay * (backoff_factor ** attempt):.1f}秒后重试",
                                exception=e,
                                function=func.__name__,
                                attempt=attempt + 1
                            )
                            import time
                            time.sleep(delay * (backoff_factor ** attempt))
                        else:
                            logger.error(
                                f"函数 {func.__name__} 重试 {max_attempts} 次后仍然失败",
                                exception=last_exception
                            )
                
                raise last_exception
            
            return wrapper
        return decorator
    
    @staticmethod
    def fallback(primary_func: Callable, fallback_func: Callable, fallback_condition: type = Exception):
        """回退装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return primary_func(*args, **kwargs)
                except fallback_condition as e:
                    logger.warning(
                        f"主函数 {primary_func.__name__} 失败，使用回退函数 {fallback_func.__name__}",
                        exception=e
                    )
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"回退函数也失败: {fallback_func.__name__}", exception=fallback_error)
                        raise e
            
            return wrapper
        return decorator


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks = []
    
    def add_check(self, name: str, check_func: Callable, critical: bool = False, threshold_ms: int = 0):
        """
        添加健康检查
        
        Args:
            name: 检查名称
            check_func: 检查函数，返回 (bool, float) 或 bool
            critical: 是否关键检查
            threshold_ms: 延迟阈值(毫秒)，超过则为"亚健康"
        """
        self.checks.append({
            'name': name,
            'func': check_func,
            'critical': critical,
            'threshold_ms': threshold_ms,
            'last_result': None,
            'last_check': None,
            'last_latency': 0
        })
    
    def run_checks(self) -> dict:
        """运行所有健康检查"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'failed_critical': 0,
            'degraded_count': 0
        }
        
        for check in self.checks:
            try:
                start_time = datetime.now()
                check_result = check['func']()
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                # 支持返回 (result, latency) 元组
                if isinstance(check_result, tuple):
                    check_result, custom_latency = check_result
                    latency_ms = custom_latency
                
                check['last_result'] = check_result
                check['last_check'] = datetime.now()
                check['last_latency'] = latency_ms
                
                # 判断状态
                if not check_result:
                    status = 'fail'
                    if check['critical']:
                        results['status'] = 'unhealthy'
                        results['failed_critical'] += 1
                elif check['threshold_ms'] > 0 and latency_ms > check['threshold_ms']:
                    status = 'degraded'
                    if results['status'] == 'healthy':
                        results['status'] = 'degraded'
                    results['degraded_count'] += 1
                else:
                    status = 'pass'
                
                results['checks'][check['name']] = {
                    'status': status,
                    'message': 'OK' if status == 'pass' else f'Latency: {latency_ms:.0f}ms' if status == 'degraded' else 'Check failed',
                    'latency_ms': latency_ms
                }
                
            except Exception as e:
                logger.error(f"健康检查失败: {check['name']}", exception=e)
                results['checks'][check['name']] = {
                    'status': 'error',
                    'message': str(e)
                }
                
                if check['critical']:
                    results['status'] = 'unhealthy'
                    results['failed_critical'] += 1
        
        return results