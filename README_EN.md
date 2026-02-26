# 🔐 Token Monitor

[![Version](https://img.shields.io/badge/Version-v2.1.0-blue.svg)](https://github.com/wuleiyuan/token-monitor/releases)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/wuleiyuan/token-monitor?style=social)](https://github.com/wuleiyuan/token-monitor/stargazers)

> English | [中文](./README.md)

**Enterprise Token Usage Monitoring System** - Real-time AI model Token consumption monitoring with multi-model, intelligent alerts, and multi-provider support, data visualization.

This is the companion monitoring system for [OpenCode Smart Model Selector](https://github.com/wuleiyuan/opencode-smart-model-selector).

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📊 **Real-time Monitoring** | Track Token consumption in real-time, multi-model comparison |
| 🏢 **Multi-Provider** | Support Google, Anthropic, OpenAI, Cohere and more |
| 📈 **Data Visualization** | Trend charts, pie charts and more |
| ⚠️ **Intelligent Alerts** | Daily limits, error rates and more |
| 🔐 **JWT Authentication** | Secure enterprise-grade authentication |
| 🏷️ **Rate Limiting** | IP-based API rate limiting |
| 💾 **Caching** | Redis caching for faster queries |
| 📋 **Data Export** | CSV/JSON export support |

## 🚀 Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment

```bash
# Copy config template
cp .env.template .env

# Edit .env file with your API keys
```

### Start Server

```bash
# Method 1: Direct run
python enterprise_api_server.py

# Method 2: Use startup script
chmod +x start_token_monitor.sh
./start_token_monitor.sh
```

Visit http://localhost:8000 after starting

Default credentials: `admin` / `admin123`

## 📁 Project Structure

```
token-monitor/
├── enterprise_api_server.py  # Main API server
├── auth.py                  # JWT authentication
├── redis_cache.py           # Cache management
├── audit_logger.py          # Audit logging
├── optimized_data_generator.py  # Data generator
├── data_models.py           # Data models
├── index.html              # Frontend page
├── requirements.txt         # Python dependencies
├── docker-compose.yml      # Docker deployment
└── .env.template          # Config template
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | Server host | 0.0.0.0 |
| `API_PORT` | Server port | 8000 |
| `SECRET_KEY` | JWT secret | random |
| `CORS_ORIGINS` | CORS config | localhost:8000 |
| `REDIS_URL` | Redis URL | memory |

### Supported Models

- **Paid Models**: gemini-3-pro
- **Free Models**: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash

## 📱 Screenshots

![Dashboard](screenshot.png)

## 🐳 Docker Deployment

```bash
docker-compose up -d
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Frontend page |
| `/api/auth/login` | POST | User login |
| `/api/usage` | GET | Get usage records |
| `/api/stats` | GET | Statistics |
| `/api/stats/history` | GET | Historical cumulative stats |
| `/api/models` | GET | Model list |
| `/api/alerts` | GET | Alert info |
| `/api/export/csv` | GET | Export CSV |
| `/api/export/json` | GET | Export JSON |

## 🤝 Companion Projects

**Token Monitor** is the companion monitoring system for [OpenCode Smart Model Selector](https://github.com/wuleiyuan/opencode-smart-model-selector).

### Usage Architecture

```
User Request → op command → Smart Model Selector (select model)
                              ↓
                        API Call → Consume Token
                              ↓
                        Token Monitor (monitor consumption)
```

| Project | GitHub | Description |
|---------|--------|-------------|
| 🧠 **Smart Model Selector** | [wuleiyuan/opencode-smart-model-selector](https://github.com/wuleiyuan/opencode-smart-model-selector) | Intelligent AI model routing |
| 🔐 **Token Monitor** | [wuleiyuan/token-monitor](https://github.com/wuleiyuan/token-monitor) | Token consumption monitoring |

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

⭐ If you find this useful, please give a Star!
