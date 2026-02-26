#!/usr/bin/env python3
"""
企业版Token监控系统API服务器
基于优化数据生成逻辑的完整实现
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from auth import (
    authenticate_user, 
    create_access_token, 
    get_current_user as auth_get_current_user,
    get_optional_user,
    MOCK_USERS_DB
)
from audit_logger import audit_logger, generate_request_id

# 导入优化的数据生成器
from optimized_data_generator import DataGenerator
from redis_cache import cache_manager, CACHE_TTL

# 创建数据生成器实例
data_generator = DataGenerator()

# 应用配置
app = FastAPI(
    title="Token Monitor Enterprise API",
    description="企业级Token使用监控系统 - 优化版",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "认证", "description": "API认证相关接口"},
        {"name": "数据查询", "description": "Token使用数据查询接口"},
        {"name": "统计分析", "description": "使用统计和分析接口"},
        {"name": "监控管理", "description": "系统监控和健康检查接口"}
    ]
)

# 安全配置
security = HTTPBearer(auto_error=False)

# 限流器配置
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """限流异常处理"""
    return JSONResponse(
        status_code=429,
        content={"detail": f"请求过于频繁，请稍后再试。限制: {exc.rate}"}
    )

# CORS配置 - 支持环境变量配置
cors_origins_env = os.getenv("CORS_ORIGINS", "http://0.0.0.0:5500,http://localhost:5500,http://0.0.0.0:8000,http://localhost:8000")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

@app.middleware("http")
async def validate_cors_origin(request: Request, call_next):
    """验证CORS Origin"""
    origin = request.headers.get("origin")
    
    # 允许的origin检查
    if origin and origin not in cors_origins:
        # 开发环境允许localhost
        if not any(localhost in origin for localhost in ["localhost", "0.0.0.0"]):
            return JSONResponse(
                status_code=403,
                content={"detail": "不允许的Origin"}
            )
    
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = origin or "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)

# 静态文件服务
app.mount("/static", StaticFiles(directory="."), name="static")

# 全局变量
background_tasks = BackgroundTasks()

# JWT认证依赖
async def get_current_user():
    """获取当前用户（JWT版）"""
    return await auth_get_current_user()

# 登录请求模型
class LoginRequest(BaseModel):
    username: str
    password: str

# 登录响应模型
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

# 数据模型
class TokenUsageRecord(BaseModel):
    timestamp: str = Field(..., description="时间戳")
    model_name: str = Field(..., description="模型名称")
    model: str = Field(..., description="简化的模型名称")
    tokens_used: int = Field(..., gt=0, description="使用的Token数量")
    cost: float = Field(..., ge=0, description="成本")
    provider: str = Field(..., description="供应商")
    session_id: Optional[str] = Field(None, description="会话ID")
    response_time: Optional[int] = Field(None, description="响应时间(ms)")
    status: str = Field(default="success", description="状态")

# 查询参数模型
class UsageQueryParams(BaseModel):
    timeRange: Optional[str] = Field("week", description="时间范围")
    modelType: Optional[str] = Field("all", description="模型类型")
    specificModel: Optional[str] = Field("all", description="具体模型")
    provider: Optional[str] = Field("all", description="供应商")
    startDate: Optional[str] = Field(None, description="开始日期")
    endDate: Optional[str] = Field(None, description="结束日期")
    limit: Optional[int] = Field(100, le=1000, description="返回数量限制")
    offset: Optional[int] = Field(0, ge=0, description="偏移量")

# 模型常量
FREE_MODELS = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
PAID_MODELS = ["gemini-3-pro"]

# 响应模型
class UsageResponse(BaseModel):
    records: List[TokenUsageRecord]
    total: int
    hasMore: bool = False

class StatsResponse(BaseModel):
    total_tokens: int = Field(..., description="总Token使用量")
    total_cost: float = Field(..., description="总成本")
    total_requests: int = Field(..., description="总请求数")
    average_tokens: float = Field(..., description="平均Token数")
    model_distribution: Dict[str, int] = Field(..., description="模型分布")
    provider_distribution: Dict[str, int] = Field(..., description="供应商分布")
    success_rate: float = Field(..., description="成功率")
    date_range: str = Field(..., description="数据时间范围")

# 内存存储
usage_data: List[Dict[str, Any]] = []

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.remove(connection)

ws_manager = ConnectionManager()

# 缓存管理器（使用redis_cache）
usage_cache = None

logger = logging.getLogger(__name__)

# 日志配置 - 添加敏感信息过滤
class SensitiveDataFilter(logging.Filter):
    """日志敏感信息过滤器"""
    
    SENSITIVE_KEYS = {'password', 'token', 'api_key', 'secret', 'authorization', 'x-api-key'}
    
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            msg_lower = record.msg.lower()
            for key in self.SENSITIVE_KEYS:
                if key in msg_lower:
                    record.msg = f"[FILTERED] {key} redacted for security"
        return True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('token_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 添加敏感信息过滤器到根日志器
root_logger = logging.getLogger()
root_logger.addFilter(SensitiveDataFilter())

@app.get("/")
async def read_root():
    """主页面"""
    return FileResponse("index.html")

@app.get("/favicon.ico")
async def favicon():
    """Favicon"""
    return FileResponse("static/favicon.ico") if os.path.exists("static/favicon.ico") else None

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.1.0",
        "data_records": len(usage_data),
        "cache": cache_manager.get_stats(),
        "features": {
            "data_generation": "optimized",
            "realistic_patterns": True,
            "smart_model_selection": True,
            "user_behavior_simulation": True,
            "redis_cache": cache_manager.enabled,
            "jwt_auth": True,
            "rate_limit": True
        }
    }

@app.get("/api/cache/clear")
async def clear_cache():
    """清除缓存"""
    count = cache_manager.clear_pattern("usage:*")
    count += cache_manager.clear_pattern("stats:*")
    return {"message": f"已清除 {count} 个缓存项"}

@app.get("/api/export/csv")
@limiter.limit("10/minute")
async def export_csv(request: Request):
    """导出CSV"""
    import csv
    from fastapi.responses import StreamingResponse
    
    def generate():
        yield '\ufeff'
        yield "时间戳,模型,类型,Token数,成本,响应时间,状态\n"
        for item in usage_data:
            yield f"{item.get('timestamp','')},{item.get('model','')},{item.get('type','')},{item.get('tokens',0)},{item.get('cost',0):.4f},{item.get('response_time',0)},{item.get('status','')}\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=token_usage.csv"}
    )

@app.get("/api/export/json")
@limiter.limit("10/minute")
async def export_json(request: Request):
    """导出JSON"""
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        usage_data,
        headers={"Content-Disposition": "attachment; filename=token_usage.json"}
    )

@app.get("/api/export/summary")
@limiter.limit("10/minute")
async def export_summary(request: Request):
    """导出统计摘要"""
    return data_generator.get_data_summary(usage_data)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时推送"""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.post("/api/ws/broadcast")
async def broadcast_message(message: dict):
    """广播消息到所有WebSocket客户端"""
    await ws_manager.broadcast(message)
    return {"status": "broadcasted", "clients": len(ws_manager.active_connections)}

# 告警配置
ALERT_THRESHOLDS = {
    "daily_limit": float(os.getenv("ALERT_DAILY_LIMIT", "100.0")),
    "hourly_limit": float(os.getenv("ALERT_HOURLY_LIMIT", "20.0")),
    "error_rate_threshold": float(os.getenv("ALERT_ERROR_RATE", "0.1")),
}

alert_history: List[dict] = []

def check_alerts():
    """检查是否触发告警"""
    global alert_history
    alerts = []
    now = datetime.now()
    
    if not usage_data:
        return alerts
    
    # 计算今日使用量
    today = now.date()
    daily_tokens = sum(
        item.get("tokens", 0) for item in usage_data 
        if datetime.fromisoformat(item.get("timestamp", now.isoformat()).replace(' ', 'T')).date() == today
    )
    
    if daily_tokens / 1000 > ALERT_THRESHOLDS["daily_limit"]:
        alerts.append({
            "type": "daily_limit",
            "message": f"今日Token使用量已达 ${daily_tokens/1000 * 0.02:.2f} (阈值: ${ALERT_THRESHOLDS['daily_limit']})",
            "severity": "warning",
            "timestamp": now.isoformat()
        })
    
    # 计算失败率
    total = len(usage_data)
    failed = sum(1 for item in usage_data if item.get("status") == "failed")
    error_rate = failed / total if total > 0 else 0
    
    if error_rate > ALERT_THRESHOLDS["error_rate_threshold"]:
        alerts.append({
            "type": "error_rate",
            "message": f"错误率 {error_rate*100:.1f}% 超过阈值 {ALERT_THRESHOLDS['error_rate_threshold']*100}%",
            "severity": "critical",
            "timestamp": now.isoformat()
        })
    
    alert_history = alerts + alert_history[:99]
    return alerts

@app.get("/api/alerts")
async def get_alerts():
    """获取当前告警"""
    return {
        "alerts": check_alerts(),
        "thresholds": ALERT_THRESHOLDS
    }

@app.get("/api/alerts/history")
async def get_alert_history(limit: int = 50):
    """获取告警历史"""
    return {"alerts": alert_history[:limit]}

@app.get("/api/audit/logs")
async def get_audit_logs(limit: int = 100):
    """获取审计日志"""
    return {"logs": audit_logger.get_recent_logs(limit)}

@app.get("/api/audit/stats")
async def get_audit_stats():
    """获取审计统计"""
    return audit_logger.get_stats()

@app.post("/api/auth/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(request: Request, login_data: LoginRequest):
    """用户登录"""
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )
    
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400,
        "user": {"username": user["username"], "role": user["role"]}
    }

@app.get("/api/auth/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """验证令牌"""
    return {"valid": True, "user": current_user}

@app.get("/api/models")
async def get_models():
    """获取模型列表"""
    return {
        "paid_models": ["gemini-3-pro"],
        "free_models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
        "supported_providers": ["google", "anthropic", "openai", "cohere"],
        "model_capabilities": {
            "gemini-3-pro": {
                "max_tokens": 4000,
                "context_window": "32k",
                "supports_functions": True,
                "cost_per_1k_tokens": 0.10
            },
            "gemini-2.5-pro": {
                "max_tokens": 2000,
                "context_window": "16k",
                "supports_functions": False,
                "cost_per_1k_tokens": 0.05
            },
            "gemini-2.5-flash": {
                "max_tokens": 1000,
                "context_window": "8k",
                "supports_functions": False,
                "cost_per_1k_tokens": 0.02
            },
            "gemini-2.0-flash": {
                "max_tokens": 500,
                "context_window": "4k",
                "supports_functions": False,
                "cost_per_1k_tokens": 0.01
            }
        }
    }

@app.get("/api/usage", response_model=UsageResponse)
@limiter.limit("60/minute")
async def get_usage(request: Request,
    params: UsageQueryParams = Depends()
):
    """获取使用记录"""
    logger.info(f"API调用: timeRange={params.timeRange}, modelType={params.modelType}, provider={params.provider}")
    
    # 尝试从缓存获取
    filters = {
        "timeRange": params.timeRange,
        "modelType": params.modelType,
        "provider": params.provider,
        "startDate": params.startDate,
        "endDate": params.endDate
    }
    try:
        filtered_data = usage_data.copy()
        
        # 时间范围和日期选择器的逻辑：日期选择优先于时间范围
        # 如果用户选择了开始日期或结束日期，则使用日期范围，忽略timeRange
        has_custom_date = params.startDate or params.endDate
        
        if not has_custom_date and params.timeRange:
            now = datetime.now()
            if params.timeRange == "day":
                # 今日
                start_date = now.strftime("%Y-%m-%d")
                end_date = now.strftime("%Y-%m-%d")
            elif params.timeRange == "week":
                # 本周（自然周：周一到周日）
                weekday = now.weekday()  # 0=周一, 6=周日
                start_date = (now - timedelta(days=weekday)).strftime("%Y-%m-%d")
                end_date = (now + timedelta(days=6-weekday)).strftime("%Y-%m-%d")
            elif params.timeRange == "month":
                # 本月（自然月）
                start_date = now.strftime("%Y-%m-01")
                if now.month == 12:
                    end_date = datetime(now.year, 12, 31).strftime("%Y-%m-%d")
                else:
                    end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
                    end_date = end_date.strftime("%Y-%m-%d")
            elif params.timeRange == "year":
                # 本年（自然年）
                start_date = datetime(now.year, 1, 1).strftime("%Y-%m-%d")
                end_date = datetime(now.year, 12, 31).strftime("%Y-%m-%d")
            
            filtered_data = [
                item for item in filtered_data 
                if start_date <= item.get("timestamp", "")[:10] <= end_date
            ]
        
        # 日期选择器过滤
        if params.startDate:
            filtered_data = [
                item for item in filtered_data 
                if item.get("timestamp", "")[:10] >= params.startDate
            ]
        
        if params.endDate:
            filtered_data = [
                item for item in filtered_data 
                if item.get("timestamp", "")[:10] <= params.endDate
            ]
        
        # 其他过滤
        if params.provider and params.provider != "all":
            provider_val = params.provider.lower()
            filtered_data = [
                item for item in filtered_data 
                if (item.get("provider") or "").lower() == provider_val
            ]
        
        # 模型过滤：具体模型 > 模型类型 (支持模糊匹配)
        if params.specificModel and params.specificModel != "all":
            search = params.specificModel.lower()
            filtered_data = [
                item for item in filtered_data 
                if search in item.get("model_name", "").lower() or search in item.get("model", "").lower()
            ]
        elif params.modelType == "free":
            filtered_data = [
                item for item in filtered_data 
                if item.get("model_name", "") in FREE_MODELS
            ]
        elif params.modelType == "paid":
            filtered_data = [
                item for item in filtered_data 
                if item.get("model_name", "") in PAID_MODELS
            ]
        
        # 分页
        total_filtered = len(filtered_data)
        offset = params.offset or 0
        limit = params.limit or 100
        end_idx = min(offset + limit, total_filtered)
        
        paginated_data = filtered_data[offset:end_idx]
        
        # 转换为响应模型
        response_records = [
            TokenUsageRecord(
                timestamp=item["timestamp"],
                model_name=item["model_name"],
                model=item.get("model", item["model_name"].replace("gemini-", "").replace("-", " ").upper()),
                tokens_used=item["tokens"],
                cost=item["cost"],
                provider=item["provider"],
                session_id=item.get("session_id"),
                response_time=item.get("responseTime"),
                status=item.get("status", "success")
            ) for item in paginated_data
        ]
        
        return UsageResponse(
            records=response_records,
            total=total_filtered,
            hasMore=end_idx < total_filtered
        )
        
    except Exception as e:
        logger.error(f"获取使用数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")

@app.get("/api/stats")
@limiter.limit("60/minute")
async def get_stats(
    request: Request,
    timeRange: str = Query("week", description="时间范围"),
    modelType: str = Query("all", description="模型类型"),
    specificModel: str = Query("all", description="具体模型"),
    provider: str = Query("all", description="供应商"),
    startDate: Optional[str] = Query(None, description="开始日期"),
    endDate: Optional[str] = Query(None, description="结束日期")
):
    """获取统计信息（支持过滤）"""
    
    # 应用过滤逻辑
    filtered_data = usage_data.copy()
    
    has_custom_date = startDate or endDate
    
    if not has_custom_date and timeRange:
        now = datetime.now()
        if timeRange == "day":
            start_date = now.strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
        elif timeRange == "week":
            weekday = now.weekday()
            start_date = (now - timedelta(days=weekday)).strftime("%Y-%m-%d")
            end_date = (now + timedelta(days=6-weekday)).strftime("%Y-%m-%d")
        elif timeRange == "month":
            start_date = now.strftime("%Y-%m-01")
            if now.month == 12:
                end_date = datetime(now.year, 12, 31).strftime("%Y-%m-%d")
            else:
                end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
                end_date = end_date.strftime("%Y-%m-%d")
        elif timeRange == "year":
            start_date = datetime(now.year, 1, 1).strftime("%Y-%m-%d")
            end_date = datetime(now.year, 12, 31).strftime("%Y-%m-%d")
        else:
            start_date = "2000-01-01"
            end_date = "2099-12-31"
        
        filtered_data = [
            item for item in filtered_data 
            if start_date <= item.get("timestamp", "")[:10] <= end_date
        ]
    elif startDate or endDate:
        s = startDate or "2000-01-01"
        e = endDate or datetime.now().strftime("%Y-%m-%d")
        filtered_data = [
            item for item in filtered_data
            if s <= item.get("timestamp", "")[:10] <= e
        ]
    
    # 模型类型过滤
    if modelType == "paid":
        filtered_data = [item for item in filtered_data if item.get("model_name") in PAID_MODELS]
    elif modelType == "free":
        filtered_data = [item for item in filtered_data if item.get("model_name") in FREE_MODELS]
    
    # 具体模型过滤
    if specificModel and specificModel != "all":
        filtered_data = [
            item for item in filtered_data 
            if specificModel.lower() in item.get("model_name", "").lower()
        ]
    
    # 供应商过滤
    if provider and provider != "all":
        filtered_data = [item for item in filtered_data if item.get("provider") == provider]
    
    if not filtered_data:
        return {
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_requests": 0,
            "average_tokens": 0.0,
            "model_distribution": {},
            "provider_distribution": {},
            "success_rate": 100.0,
            "date_range": "N/A"
        }
    
    try:
        total_tokens = sum(item.get("tokens", 0) for item in filtered_data)
        total_cost = sum(item.get("cost", 0.0) for item in filtered_data)
        total_requests = len(filtered_data)
        average_tokens = total_tokens / total_requests if total_requests > 0 else 0
        
        # 模型分布统计
        model_distribution = {}
        for item in filtered_data:
            model = item.get("model_name", "unknown")
            model_distribution[model] = model_distribution.get(model, 0) + 1
        
        # 供应商分布统计
        provider_distribution = {}
        for item in filtered_data:
            provider = item.get("provider", "unknown")
            provider_distribution[provider] = provider_distribution.get(provider, 0) + 1
        
        # 成功率统计
        success_count = sum(1 for item in filtered_data if item.get("status") == "success")
        success_rate = (success_count / total_requests) * 100 if total_requests > 0 else 100.0
        
        return StatsResponse(
            total_tokens=total_tokens,
            total_cost=total_cost,
            total_requests=total_requests,
            average_tokens=average_tokens,
            model_distribution=model_distribution,
            provider_distribution=provider_distribution,
            success_rate=success_rate,
            date_range=f"{start_date} 至 {end_date}"
        )
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@app.get("/api/stats/history")
@limiter.limit("60/minute")
async def get_history_stats(request: Request):
    """获取历史累计统计（不受筛选影响）"""
    if not usage_data:
        return {
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_requests": 0,
            "unique_models": 0,
            "unique_providers": 0,
            "date_range": "N/A"
        }
    
    try:
        total_tokens = sum(item.get("tokens", 0) for item in usage_data)
        total_cost = sum(item.get("cost", 0.0) for item in usage_data)
        total_requests = len(usage_data)
        
        # 唯一模型数
        unique_models = len(set(item.get("model_name", "") for item in usage_data))
        
        # 唯一供应商数
        unique_providers = len(set(item.get("provider", "") for item in usage_data))
        
        # 数据时间范围
        timestamps = [item.get("timestamp", "") for item in usage_data if item.get("timestamp")]
        if timestamps:
            date_range = f"{min(timestamps)[:10]} 至 {max(timestamps)[:10]}"
        else:
            date_range = "N/A"
        
        return {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "total_requests": total_requests,
            "unique_models": unique_models,
            "unique_providers": unique_providers,
            "date_range": date_range
        }
        
    except Exception as e:
        logger.error(f"获取历史统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史统计失败: {str(e)}")

@app.post("/api/usage")
@limiter.limit("30/minute")
async def record_usage(request: Request,
    record: TokenUsageRecord
):
    """记录使用情况"""
    try:
        # 添加记录
        new_record = {
            "timestamp": record.timestamp,
            "model_name": record.model_name,
            "model": record.model,
            "tokens_used": record.tokens_used,
            "cost": record.cost,
            "provider": record.provider,
            "session_id": record.session_id,
            "responseTime": record.response_time,
            "status": record.status
        }
        
        usage_data.append(new_record)
        
        logger.info(f"记录使用情况: {record.model_name} - {record.tokens_used} tokens")
        
        return {
            "status": "success",
            "message": "Usage recorded successfully",
            "record_id": len(usage_data)
        }
        
    except Exception as e:
        logger.error(f"记录使用失败: {e}")
        raise HTTPException(status_code=500, detail=f"记录失败: {str(e)}")

@app.get("/api/summary")
@limiter.limit("60/minute")
async def get_summary(request: Request):
    """获取数据摘要"""
    return data_generator.get_data_summary(usage_data)

@app.delete("/api/usage/clear")
async def clear_data():
    """清空所有数据"""
    global usage_data
    usage_data.clear()
    
    cache_manager.clear_pattern("usage:*")
    
    logger.info("所有使用数据已清空，缓存已失效")
    return {"status": "success", "message": "All data cleared"}

# 启动函数
def main():
    """主启动函数"""
    logger.info("🚀 启动企业版Token监控系统...")
    
    # 初始化数据
    global usage_data
    usage_data = data_generator.generate_historical_data(30)
    logger.info(f"已生成 {len(usage_data)} 条历史数据")
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"服务器将在 http://{host}:{port} 启动")
    
    import uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()