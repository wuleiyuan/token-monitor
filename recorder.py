#!/usr/bin/env python3
"""
Token使用量记录脚本
用于记录OpenCode中各个API的Token使用情况
"""

import json
import sqlite3
import datetime
import os
import random
from pathlib import Path
from typing import Dict, List, Optional

class TokenUsageRecorder:
    def __init__(self):
        base_dir = Path(__file__).parent
        self.db_path = str(base_dir / "token_usage.db")
        self.config_file = str(Path.home() / "LocalProjects/OpenCode/oh-my-opencode.json")
        self.env_file = str(Path.home() / ".config/opencode/.env")
        
    def init_database(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
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
                user_id TEXT DEFAULT 'default'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_config(self) -> Dict:
        """加载OpenCode配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            return {}
    
    def record_api_usage(self, model_name: str, tokens_used: int, 
                        cost: float, response_time: int = 0,
                        status: str = 'success', request_type: str = 'chat'):
        """记录API使用情况"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确定模型类型和提供商
            model_type, api_provider = self.get_model_info(model_name)
            
            cursor.execute('''
                INSERT INTO token_usage 
                (model_name, model_type, tokens_used, cost, response_time, status, api_provider, request_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model_name, model_type, tokens_used, cost, 
                response_time, status, api_provider, request_type
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 记录成功: {model_name} - {tokens_used} tokens - ¥{cost}")
            
        except Exception as e:
            print(f"❌ 记录失败: {e}")
    
    def get_model_info(self, model_name: str) -> tuple:
        """获取模型信息"""
        model_mapping = {
            # Claude模型
            'claude-3-5-sonnet-20241022': ('paid', 'anthropic'),
            'claude-3-haiku-20240307': ('paid', 'anthropic'),
            
            # OpenAI模型
            'gpt-4o': ('paid', 'openai'),
            'gpt-4o-mini': ('paid', 'openai'),
            'gpt-3.5-turbo': ('paid', 'openai'),
            
            # Google模型
            'gemini-2.5-flash': ('free', 'google'),
            'gemini-2.5-pro': ('free', 'google'),
            'gemini-2.0-flash-exp': ('free', 'google'),
            'gemini-pro': ('free', 'google'),
            
            # MinMax模型
            'MiniMax-M2.1': ('free', 'minimax'),
            'MiniMax-M2.1-lightning': ('free', 'minimax'),
            
            # 智谱AI模型
            'glm-4': ('free', 'zhipuai'),
            'glm-4-turbo': ('free', 'zhipuai'),
            'glm-3-turbo': ('free', 'zhipuai'),
            
            # DeepSeek模型
            'deepseek-chat': ('free', 'deepseek'),
            
            # Mistral模型
            'mistral-large-2402': ('paid', 'mistral'),
            'mistral-tiny': ('paid', 'mistral'),
            
            # Cohere模型
            'command-r-plus': ('paid', 'cohere'),
            'command-light': ('paid', 'cohere'),
        }
        
        return model_mapping.get(model_name, ('unknown', 'unknown'))
    
    def simulate_usage_data(self, days: int = 7):
        """生成模拟使用数据"""
        print(f"🔄 生成过去{days}天的模拟数据...")
        
        models = [
            ('claude-3-5-sonnet-20241022', 0.015),  # $0.015 per 1K tokens
            ('gpt-4o', 0.005),                        # $0.005 per 1K tokens
            ('gemini-2.5-flash', 0.000075),           # $0.000075 per 1K tokens
            ('MiniMax-M2.1', 0.001),                   # $0.001 per 1K tokens
            ('glm-4', 0.001),                          # $0.001 per 1K tokens
            ('deepseek-chat', 0.00014)                 # $0.00014 per 1K tokens
        ]
        
        now = datetime.datetime.now()
        
        for day in range(days):
            date = now - datetime.timedelta(days=day)
            
            # 每天生成10-50条记录
            daily_records = random.randint(10, 50)
            
            for _ in range(daily_records):
                model, price_per_1k = random.choice(models)
                
                # 随机生成token数量 (100-5000)
                tokens = random.randint(100, 5000)
                
                # 计算成本
                cost = (tokens / 1000) * price_per_1k
                
                # 随机生成响应时间 (500-3000ms)
                response_time = random.randint(500, 3000)
                
                # 随机生成状态 (90%成功)
                status = 'success' if random.random() > 0.1 else 'error'
                
                # 生成随机时间戳
                hours = random.uniform(0, 24)
                minutes = random.uniform(0, 60)
                timestamp = date.replace(hour=int(hours), minute=int(minutes))
                
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    model_type, api_provider = self.get_model_info(model)
                    
                    cursor.execute('''
                        INSERT INTO token_usage 
                        (timestamp, model_name, model_type, tokens_used, cost, response_time, status, api_provider, request_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        timestamp, model, model_type, tokens, cost,
                        response_time, status, api_provider, 'chat'
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                except Exception as e:
                    print(f"❌ 生成数据失败: {e}")
        
        print(f"✅ 模拟数据生成完成！")
    
    def get_usage_summary(self, days: int = 7) -> Dict:
        """获取使用摘要"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(tokens_used) as total_tokens,
                    SUM(cost) as total_cost,
                    AVG(response_time) as avg_response_time,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_calls,
                    COUNT(CASE WHEN model_type = 'free' THEN 1 END) as free_calls,
                    COUNT(CASE WHEN model_type = 'paid' THEN 1 END) as paid_calls
                FROM token_usage 
                WHERE DATE(timestamp) >= DATE('now', '-{} days')
            '''.format(days))
            
            result = cursor.fetchone()
            
            summary = {
                'total_calls': result[0] or 0,
                'total_tokens': result[1] or 0,
                'total_cost': result[2] or 0,
                'avg_response_time': result[3] or 0,
                'success_calls': result[4] or 0,
                'success_rate': (result[4] / result[0] * 100) if result[0] > 0 else 0,
                'free_calls': result[5] or 0,
                'paid_calls': result[6] or 0,
                'period_days': days
            }
            
            conn.close()
            return summary
            
        except Exception as e:
            print(f"❌ 获取摘要失败: {e}")
            return {}
    
    def export_data(self, format: str = 'json', days: int = 30) -> str:
        """导出数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM token_usage 
                WHERE DATE(timestamp) >= DATE('now', '-{} days')
                ORDER BY timestamp DESC
            '''.format(days))
            
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            conn.close()
            
            if format == 'json':
                data = []
                for row in rows:
                    data.append(dict(zip(columns, row)))
                return json.dumps(data, indent=2, ensure_ascii=False)
            
            elif format == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(columns)
                writer.writerows(rows)
                return output.getvalue()
            
            return ""
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return ""

def main():
    """主函数"""
    recorder = TokenUsageRecorder()
    
    # 初始化数据库
    recorder.init_database()
    
    print("🔥 Token使用量记录工具")
    print("=" * 50)
    print("1. 生成模拟数据")
    print("2. 查看使用摘要")
    print("3. 导出数据")
    print("4. 手动记录使用")
    print("=" * 50)
    
    choice = input("请选择操作 (1-4): ").strip()
    
    if choice == '1':
        days = input("生成多少天的数据? (默认7天): ").strip()
        days = int(days) if days else 7
        recorder.simulate_usage_data(days)
        
    elif choice == '2':
        days = input("查看多少天的摘要? (默认7天): ").strip()
        days = int(days) if days else 7
        summary = recorder.get_usage_summary(days)
        
        print(f"\n📊 过去{days}天使用摘要:")
        print(f"总调用次数: {summary['total_calls']}")
        print(f"总Token使用: {summary['total_tokens']:,}")
        print(f"总成本: ¥{summary['total_cost']:.4f}")
        print(f"平均响应时间: {summary['avg_response_time']:.0f}ms")
        print(f"成功率: {summary['success_rate']:.1f}%")
        print(f"免费调用: {summary['free_calls']}")
        print(f"付费调用: {summary['paid_calls']}")
        
    elif choice == '3':
        format_choice = input("导出格式 (json/csv): ").strip().lower()
        days = input("导出多少天的数据? (默认30天): ").strip()
        days = int(days) if days else 30
        
        data = recorder.export_data(format_choice, days)
        
        filename = f"token_usage_{days}days.{format_choice}"
        filepath = f"/Users/leiyuanwu/网页小游/token-monitor/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(data)
        
        print(f"✅ 数据已导出到: {filepath}")
        
    elif choice == '4':
        model = input("模型名称: ").strip()
        tokens = input("Token数量: ").strip()
        cost = input("成本 (元): ").strip()
        
        try:
            recorder.record_api_usage(
                model_name=model,
                tokens_used=int(tokens),
                cost=float(cost)
            )
        except ValueError:
            print("❌ 输入格式错误")
    
    else:
        print("❌ 无效选择")

if __name__ == "__main__":
    main()