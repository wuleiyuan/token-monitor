#!/usr/bin/env python3
"""
优化的数据生成器模块
用于企业版Token监控系统
基于简化版的数据生成逻辑进行优化
"""

import datetime
import random
from typing import Dict, Any, List, Optional

class DataGenerator:
    """数据生成器类"""
    
    def __init__(self, seed: Optional[int] = None, use_config_prices: bool = True):
        """
        初始化数据生成器
        
        Args:
            seed: 随机数种子，用于测试可重复性。默认None表示随机。
            use_config_prices: 是否使用配置文件中的价格。默认True。
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)
        
        # 默认价格
        default_prices = {
            "gemini-2.0-flash": 0.01,
            "gemini-2.5-flash": 0.02, 
            "gemini-2.5-pro": 0.05,
            "gemini-3-pro": 0.1
        }
        
        # 尝试从配置获取价格
        if use_config_prices:
            try:
                from config_manager import config
                config_prices = config.get_cost_per_1k()
                # 映射配置价格到模型
                self.cost_per_token = {
                    "gemini-2.0-flash": config_prices.get("gemini-2.0-flash", default_prices["gemini-2.0-flash"]),
                    "gemini-2.5-flash": config_prices.get("gemini-2.5-flash", default_prices["gemini-2.5-flash"]),
                    "gemini-2.5-pro": config_prices.get("gemini-2.5-pro", default_prices["gemini-2.5-pro"]),
                    "gemini-3-pro": config_prices.get("gemini-3-pro", default_prices["gemini-3-pro"])
                }
            except ImportError:
                self.cost_per_token = default_prices
        else:
            self.cost_per_token = default_prices
        
        self.models = [
            {"name": "gemini-2.0-flash", "tokens": 500, "weight": 4, "type": "free"},
            {"name": "gemini-2.5-flash", "tokens": 800, "weight": 3, "type": "free"},
            {"name": "gemini-2.5-pro", "tokens": 1200, "weight": 2, "type": "free"},
            {"name": "gemini-3-pro", "tokens": 2000, "weight": 1, "type": "paid"}
        ]
    
    def generate_historical_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """生成历史数据"""
        print(f"📊 生成过去{days}天的历史数据...")
        data = []
        now = datetime.datetime.now()
        
        for days_ago in range(days, 0, -1):
            current_date = now - datetime.timedelta(days=days_ago)
            
            # 动态生成每天记录数量（越近的日期记录越多）
            base_records = max(1, min(8, int((days - days_ago) / 3) + 2))
            
            for record_idx in range(base_records):
                # 生成时间分布（工作时间9:00-21:00）
                hour = 9 + (record_idx * 4) % 13  # 避开深夜时间
                minute = random.randint(0, 59)
                
                timestamp = current_date.replace(hour=hour, minute=minute).strftime("%Y-%m-%d %H:%M:%S")
                
                # 智能选择模型（根据真实使用模式）
                model = self._smart_select_model(current_date.hour)
                
                # 添加随机变化
                token_variation = random.randint(-300, 500)
                tokens = max(50, model["tokens"] + token_variation)
                
                # 计算成本
                cost = (tokens / 1000) * self.cost_per_token[model["name"]]
                
                # 模拟响应时间（与模型复杂度相关）
                base_response_time = {
                    "gemini-2.0-flash": 120,
                    "gemini-2.5-flash": 180,
                    "gemini-2.5-pro": 300,
                    "gemini-3-pro": 450
                }
                
                response_time = base_response_time[model["name"]] + random.randint(-50, 100)
                
                # 状态模拟（大部分成功）
                status = random.choices(
                    ["success", "success", "success", "failed"], 
                    weights=[95, 95, 95, 5]  # 95%成功率
                )[0]
                
                data.append({
                    "timestamp": timestamp,
                    "model_name": model["name"],
                    "model": model["name"].replace("gemini-", "").replace("-", " ").upper(),
                    "tokens_used": tokens,
                    "tokens": tokens,
                    "cost": round(cost, 4),
                    "provider": "google",
                    "session_id": f"historical_{days_ago}_{record_idx}",
                    "type": model["type"],
                    "responseTime": response_time,
                    "status": status
                })
        
        print(f"✅ 已生成 {len(data)} 条历史数据")
        return data
    
    def generate_today_data(self, records_count: int = 5) -> List[Dict[str, Any]]:
        """生成今日数据"""
        print(f"📊 生成今日{records_count}条数据...")
        now = datetime.datetime.now()
        data = []
        
        # 今日数据应该更加真实，体现实际使用模式
        today_scenarios = [
            {
                "hour": 9, "minute": 30, "model": "gemini-2.0-flash", "tokens": 600,
                "scenario": "晨间快速查询"
            },
            {
                "hour": 11, "minute": 45, "model": "gemini-2.5-flash", "tokens": 1200,
                "scenario": "日常工作处理"
            },
            {
                "hour": 14, "minute": 15, "model": "gemini-2.5-pro", "tokens": 800,
                "scenario": "下午代码生成"
            },
            {
                "hour": 16, "minute": 45, "model": "gemini-3-pro", "tokens": 1500,
                "scenario": "复杂任务处理"
            },
            {
                "hour": 20, "minute": 30, "model": "gemini-2.5-flash", "tokens": 400,
                "scenario": "晚间学习"
            }
        ]
        
        for i, scenario in enumerate(today_scenarios[:records_count]):
            timestamp = now.replace(
                hour=scenario["hour"], 
                minute=scenario["minute"]
            ).strftime("%Y-%m-%d %H:%M:%S")
            
            model = next(m for m in self.models if m["name"] == scenario["model"])
            
            # 计算成本
            cost = (scenario["tokens"] / 1000) * self.cost_per_token[model["name"]]
            
            # 响应时间基于场景调整
            base_time = {
                "gemini-2.0-flash": 120, "gemini-2.5-flash": 180,
                "gemini-2.5-pro": 300, "gemini-3-pro": 450
            }
            response_time = base_time[model["name"]] + random.randint(-30, 60)
            
            data.append({
                "timestamp": timestamp,
                "model_name": model["name"],
                "model": model["name"].replace("gemini-", "").replace("-", " ").upper(),
                "tokens_used": scenario["tokens"],
                "tokens": scenario["tokens"],
                "cost": round(cost, 4),
                "provider": "google",
                "session_id": f"today_scenario_{i}",
                "type": model["type"],
                "responseTime": response_time,
                "status": "success",
                "scenario": scenario["scenario"]
            })
        
        print(f"✅ 已生成今日{len(data)}条数据")
        return data
    
    def _smart_select_model(self, hour: int) -> Dict[str, Any]:
        """根据时间智能选择模型"""
        # 工作时间更可能使用复杂模型
        if 9 <= hour <= 17:
            # 工作时间：有更高概率使用付费模型
            weights = [2, 3, 2, 1]  # 付费模型权重更高
        else:
            # 非工作时间：更多使用免费模型
            weights = [4, 3, 2, 1]
        
        return random.choices(self.models, weights=weights)[0]
    
    def generate_realistic_data(self, total_records: int = 200) -> List[Dict[str, Any]]:
        """生成真实感的数据（内存优化版）"""
        print(f"📊 生成{total_records}条真实感数据...")
        now = datetime.datetime.now()
        
        # 优化：动态计算需要的天数，避免生成过多数据
        # 假设每天最多8条记录，根据total_records计算需要的天数
        max_days_needed = min(90, (total_records // 3) + 10)
        
        data = []
        
        # 只生成需要的天数范围
        for days_ago in range(max_days_needed, 0, -1):
            if len(data) >= total_records:
                break
                
            current_date = now - datetime.timedelta(days=days_ago)
            
            # 每天随机生成0-8条记录
            daily_records = random.randint(0, 8)
            
            for i in range(daily_records):
                if len(data) >= total_records:
                    break
                    
                # 智能时间分布
                if 6 <= i <= 8:
                    hour = 9 + i  # 9:00-17:00
                else:
                    hour = random.choice([19, 20, 21])
                
                timestamp = current_date.replace(hour=hour, minute=random.randint(0, 59))
                
                # 周期模式
                if current_date.weekday() >= 5:
                    weights = [3, 4, 2, 1]
                else:
                    weights = [4, 3, 2, 1]
                
                model = random.choices(self.models, weights=weights)[0]
                
                # 错误重试模式
                if random.random() < 0.1:
                    tokens = random.randint(100, 500)
                    response_time = random.randint(1000, 3000)
                    status = "failed"
                else:
                    token_variation = random.randint(-200, 800)
                    tokens = max(50, model["tokens"] + token_variation)
                    base_time = {
                        "gemini-2.0-flash": 120, "gemini-2.5-flash": 180,
                        "gemini-2.5-pro": 300, "gemini-3-pro": 450
                    }
                    response_time = base_time[model["name"]] + random.randint(-50, 200)
                    status = "success"
                
                cost = (tokens / 1000) * self.cost_per_token[model["name"]]
                
                data.append({
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "model_name": model["name"],
                    "model": model["name"].replace("gemini-", "").replace("-", " ").upper(),
                    "tokens_used": tokens,
                    "tokens": tokens,
                    "cost": round(cost, 4),
                    "provider": "google",
                    "session_id": f"realistic_{days_ago}_{i}",
                    "type": model["type"],
                    "responseTime": response_time,
                    "status": status
                })
        
        # 按时间排序
        data.sort(key=lambda x: x["timestamp"], reverse=False)
        
        print(f"✅ 已生成{len(data)}条真实感数据")
        return data[:total_records]
    
    def get_data_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取数据摘要"""
        if not data:
            return {"total_records": 0}
        
        total_tokens = sum(item["tokens"] for item in data)
        total_cost = sum(item["cost"] for item in data)
        model_stats = {}
        provider_stats = {}
        
        for item in data:
            model = item["model_name"]
            model_stats[model] = model_stats.get(model, 0) + 1
            
            provider = item["provider"]
            provider_stats[provider] = provider_stats.get(provider, 0) + 1
        
        return {
            "total_records": len(data),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "model_stats": model_stats,
            "provider_stats": provider_stats,
            "date_range": f"{data[-1]['timestamp'][:10]} 至 {data[0]['timestamp'][:10]}" if data else "N/A"
        }