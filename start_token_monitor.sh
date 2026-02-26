#!/bin/bash

# Token监控系统启动脚本

echo "🚀 Token监控系统启动中..."
echo "📍 目录: $(pwd)"
echo "⏰ 时间: $(date)"
echo ""

# 检查是否已有进程在运行
if pgrep -f "simple_fastapi.py" > /dev/null; then
    echo "⚠️  Token监控系统已在运行中！"
    echo "📊 进程信息:"
    ps aux | grep simple_fastapi | grep -v grep
    echo ""
    echo "🌐 访问地址: http://127.0.0.1:8000"
    echo "📄 API文档: http://127.0.0.1:8000/docs"
    echo "🏥 健康检查: http://127.0.0.1:8000/api/health"
    exit 0
fi

# 启动新的服务进程
echo "🔧 启动FastAPI服务..."
nohup python3 simple_fastapi.py > token_monitor.log 2>&1 &
PROCESS_ID=$!

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 3

# 检查服务是否成功启动
if curl -s http://127.0.0.1:8000/api/health > /dev/null; then
    echo ""
    echo "✅ Token监控系统启动成功！"
    echo "📋 服务信息:"
    echo "  🆔 进程ID: $PROCESS_ID"
    echo "  🌐 访问地址: http://127.0.0.1:8000"
    echo "  📄 API文档: http://127.0.0.1:8000/docs"
    echo "  🏥 健康检查: http://127.0.0.1:8000/api/health"
    echo "  📊 模型信息: http://127.0.0.1:8000/api/models"
    echo "  📋 日志文件: token_monitor.log"
    echo ""
    echo "🎮 管理命令:"
    echo "  📖 查看日志: tail -f token_monitor.log"
    echo "  🛑 停止服务: pkill -f simple_fastapi.py"
    echo "  📊 检查状态: curl http://127.0.0.1:8000/api/health"
    echo ""
    echo "🎉 系统已就绪，请访问 http://127.0.0.1:8000"
else
    echo "❌ 服务启动失败，请检查日志:"
    cat token_monitor.log
    exit 1
fi