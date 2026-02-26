# 🔐 Token Monitor

[![Version](https://img.shields.io/badge/Version-v2.1.0-blue.svg)](https://github.com/wuleiyuan/token-monitor/releases)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/wuleiyuan/token-monitor?style=social)](https://github.com/wuleiyuan/token-monitor/stargazers)

> 🇨🇳 中文 | [English](./README_EN.md)

**企业级 Token 使用监控系统** - 实时监控 AI 模型 Token 消耗，支持多模型、多供应商，提供智能告警和数据可视化。

本项目是 [OpenCode Smart Model Selector](https://github.com/wuleiyuan/opencode-smart-model-selector) 的配套监控系统。

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 📊 **实时监控** | 实时追踪 Token 消耗，支持多模型对比 |
| 🏢 **多供应商** | 支持 Google、Anthropic、OpenAI、Cohere 等 |
| 📈 **数据可视化** | 趋势图、饼图等多种图表展示 |
| ⚠️ **智能告警** | 支持日限额、错误率等多种告警 |
| 🔐 **JWT 认证** | 安全的企业级认证 |
| 🏷️ **速率限制** | 基于 IP 的 API 限流保护 |
| 💾 **缓存支持** | Redis 缓存加速查询 |
| 📋 **数据导出** | 支持 CSV/JSON 导出 |

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

```bash
# 复制配置模板
cp .env.template .env

# 编辑 .env 文件，配置你的 API Key
```

### 启动服务

```bash
# 方式1: 直接运行
python enterprise_api_server.py

# 方式2: 使用启动脚本
chmod +x start_token_monitor.sh
./start_token_monitor.sh
```

服务启动后访问 http://localhost:8000

默认账户: `admin` / `admin123`

## 📁 项目结构

```
token-monitor/
├── enterprise_api_server.py  # 主 API 服务器
├── auth.py                  # JWT 认证
├── redis_cache.py           # 缓存管理
├── audit_logger.py          # 审计日志
├── optimized_data_generator.py  # 数据生成器
├── data_models.py           # 数据模型
├── index.html               # 前端页面
├── requirements.txt         # Python 依赖
├── docker-compose.yml       # Docker 部署
└── .env.template           # 配置模板
```

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_HOST` | 服务地址 | 0.0.0.0 |
| `API_PORT` | 服务端口 | 8000 |
| `SECRET_KEY` | JWT 密钥 | random |
| `CORS_ORIGINS` | CORS 配置 | localhost:8000 |
| `REDIS_URL` | Redis 地址 | memory |

### 支持的模型

- **付费模型**: gemini-3-pro
- **免费模型**: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash

## 📱 界面预览

![Dashboard](screenshot.png)

## 🐳 Docker 部署

```bash
docker-compose up -d
```

## 🔌 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端页面 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/usage` | GET | 获取使用记录 |
| `/api/stats` | GET | 统计数据 |
| `/api/stats/history` | GET | 历史累计统计 |
| `/api/models` | GET | 模型列表 |
| `/api/alerts` | GET | 告警信息 |
| `/api/export/csv` | GET | 导出 CSV |
| `/api/export/json` | GET | 导出 JSON |

## 🤝 配套项目

**Token Monitor** 是 [OpenCode Smart Model Selector](https://github.com/wuleiyuan/opencode-smart-model-selector) 的配套监控系统。

### 配合使用架构

```
用户请求 → op 命令 → Smart Model Selector (选择模型) 
                              ↓
                        API 调用 → 消耗 Token
                              ↓
                        Token Monitor (监控消耗)
```

| 项目 | GitHub | 说明 |
|------|--------|------|
| 🧠 **Smart Model Selector** | [wuleiyuan/opencode-smart-model-selector](https://github.com/wuleiyuan/opencode-smart-model-selector) | 智能模型调度，自动选择最优 AI 模型 |
| 🔐 **Token Monitor** | [wuleiyuan/token-monitor](https://github.com/wuleiyuan/token-monitor) | Token 消耗监控，实时追踪使用量 |

- [OpenCode Smart Model Selector](https://github.com/wuleiyuan/opencode-smart-model-selector) - 智能模型调度系统

## 📄 许可证

MIT License - 查看 [LICENSE](LICENSE) 了解详情

---

⭐ 如果对你有帮助，请给个 Star！
