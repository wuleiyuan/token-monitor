#!/usr/bin/env python3
"""
配置管理模块
统一管理所有配置项，提高安全性和可维护性
"""

import configparser
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv


class ConfigManager:
    """配置管理器 - 提供统一的配置接口"""
    
    def __init__(self, config_file: Optional[str] = None):
        # 优先加载环境变量
        self._load_env()
        
        self.config_file = config_file or self._get_default_config_path()
        self.config = configparser.ConfigParser()
        self._load_config()
    
    def _load_env(self):
        """加载环境变量"""
        try:
            # 尝试加载.env文件
            env_file = Path(__file__).parent / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                logging.info(f"环境变量文件加载成功: {env_file}")
        except ImportError:
            logging.warning("python-dotenv未安装，跳过.env文件加载")
        except Exception as e:
            logging.warning(f"环境变量加载失败: {e}")
        
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        script_dir = Path(__file__).parent
        config_path = script_dir / "config.ini"
        return str(config_path)
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding='utf-8')
                logging.info(f"配置文件加载成功: {self.config_file}")
            else:
                logging.warning(f"配置文件不存在，使用默认配置: {self.config_file}")
                self._create_default_config()
        except Exception as e:
            logging.error(f"配置文件加载失败: {e}")
            raise ConfigError(f"Failed to load config: {e}")
    
    def _create_default_config(self):
        """创建默认配置"""
        default_config = """
[database]
path = token_usage.db
backup_enabled = true
backup_interval_hours = 24

[logging]
level = INFO
file = token_monitor.log
max_file_size_mb = 10

[security]
allowed_origins = *
require_auth = false
auth_token =

[api]
port = 5000
host = 127.0.0.1
max_connections = 100
request_timeout_seconds = 30

[cost_calculation]
default_currency = CNY
precision = 4

[google]
# Google API 密钥配置 - 已移至环境变量
# 请使用 .env 文件或系统环境变量配置API密钥
paid_model = gemini-3-pro

[models]
paid_providers = anthropic,openai,cohere
paid_models = gemini-3-pro
free_rate_limit_models = gemini-2.5-pro,gemini-2.5-flash,gemini-2.0-flash

[data_retention]
days_to_keep = 365
cleanup_interval_hours = 24
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(default_config.strip())
            self.config.read(self.config_file, encoding='utf-8')
        except Exception as e:
            logging.error(f"创建默认配置失败: {e}")
    
    def get(self, section: str, key: str, fallback: Any = None) -> Optional[str]:
        """获取配置值 - 优先级：环境变量 > 配置文件 > 默认值"""
        env_key = f"{section.upper()}_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
            
        try:
            return self.config.get(section, key, fallback=str(fallback) if fallback is not None else None)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return str(fallback) if fallback is not None else None
    
    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """获取整数配置"""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_boolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """获取布尔配置"""
        try:
            return self.config.getboolean(section, key, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_list(self, section: str, key: str, fallback: Optional[List[str]] = None) -> List[str]:
        """获取列表配置（逗号分隔）"""
        # 优先从环境变量获取
        env_key = f"{section.upper()}_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return [item.strip() for item in env_value.split(',') if item.strip()]
            
        try:
            value = self.config.get(section, key, fallback='')
            return [item.strip() for item in value.split(',') if item.strip()]
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback or []
    
    @property
    def db_path(self) -> str:
        """获取数据库路径"""
        db_name = self.get('database', 'path') or 'token_usage.db'
        script_dir = Path(__file__).parent
        return str(script_dir / db_name)
    
    @property
    def log_file(self) -> str:
        """获取日志文件路径"""
        log_name = self.get('logging', 'file') or 'token_monitor.log'
        script_dir = Path(__file__).parent
        return str(script_dir / log_name)
    
    @property
    def paid_providers(self) -> List[str]:
        """付费提供商列表"""
        return self.get_list('models', 'paid_providers', ['anthropic', 'openai', 'cohere'])
    
    @property
    def paid_models(self) -> List[str]:
        """付费模型列表"""
        return self.get_list('models', 'paid_models', ['gemini-3-pro'])
    
    @property
    def google_paid_api_key(self) -> str:
        """Google付费API密钥"""
        return self.get('google', 'paid_api_key') or ''
    
    @property
    def google_free_api_keys(self) -> List[str]:
        """Google免费API密钥列表"""
        return self.get_list('google', 'free_api_keys', [])
    
    def is_paid_model(self, provider: str, model_name: str) -> bool:
        """判断是否为付费模型 - 更新为精确匹配"""
        # Google API的付费模型判断
        if provider == 'google' and 'gemini-3-pro' in model_name.lower():
            return True
        
        # 其他付费提供商
        if provider in self.paid_providers:
            return True
        
        # 特定付费模型
        for paid_model in self.paid_models:
            if paid_model.lower() in model_name.lower():
                return True
        
        return False
    
    def get_cost_per_1k(self) -> Dict[str, float]:
        """获取每1K tokens的成本"""
        return {
            'claude-3-5-sonnet-20241022': 0.015,
            'gpt-4o': 0.005,
            'gpt-4o-mini': 0.00015,
            'gemini-3-pro': 0.0025,
            'gemini-2.5-pro': 0.00125,
            'gemini-2.5-flash': 0.000075,
            'gemini-2.0-flash': 0.00005,
            'MiniMax-M2.1': 0.001,
            'MiniMax-M2.1-lightning': 0.0005,
            'glm-4': 0.001,
            'glm-4-turbo': 0.0008,
            'xiaomi-gpt-turbo': 0.0001,
            'xiaomi-gpt': 0.0003,
            'deepseek-chat': 0.00014
        }
    
    @property
    def db_host(self) -> str:
        """数据库主机"""
        return os.getenv('DB_HOST', 'localhost')
    
    @property
    def db_port(self) -> int:
        """数据库端口"""
        return int(os.getenv('DB_PORT', '5432'))
    
    @property
    def db_name(self) -> str:
        """数据库名称"""
        return self.get('database', 'name') or os.getenv('DB_NAME', 'token_monitor')
    
    @property
    def db_user(self) -> str:
        """数据库用户"""
        return self.get('database', 'username') or os.getenv('DB_USER', 'postgres')
    
    @property
    def db_password(self) -> str:
        """数据库密码"""
        return self.get('database', 'password') or os.getenv('DB_PASSWORD', '')
    
    @property
    def redis_host(self) -> str:
        """Redis主机"""
        return os.getenv('REDIS_HOST', 'localhost')
    
    @property
    def redis_port(self) -> int:
        """Redis端口"""
        return int(os.getenv('REDIS_PORT', '6379'))


class ConfigError(Exception):
    """配置相关错误"""
    pass


# 全局配置实例
config = ConfigManager()