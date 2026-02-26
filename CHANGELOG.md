# 📋 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.0] - 2026-02-26

### ✨ Added
- Historical cumulative data support (不受筛选影响)
- Filter bar with time range, model type, provider filters
- Model distribution chart (doughnut chart)
- Token usage trend chart (line chart)
- Real-time alerts panel
- JWT authentication
- Rate limiting with slowapi
- Redis/memory caching support

### 🎨 Improved
- Midnight Deep Blue theme with neon accents
- Glassmorphism UI effects
- Responsive design
- Animated statistics cards

### 🔧 Fixed
- Filter logic (natural week/month/year)
- Cache key includes all filter parameters

---

## [2.0.0] - 2026-02-16

### ✨ Added
- Enterprise API server with FastAPI
- Multi-provider support (Google, Anthropic, OpenAI, Cohere)
- Data visualization with Chart.js
- Alert system (daily limit, error rate)
- Audit logging
- CSV/JSON export
- Docker deployment support

### 🎨 Improved
- Modern dark theme
- Responsive dashboard layout
- User authentication

---

## [1.0.0] - 2026-02-03

### ✨ Added
- Initial release
- Basic token usage tracking
- SQLite database
- Simple API endpoints

---

## 🔮 Coming Soon

- [ ] PyPI package release
- [ ] More chart types
- [ ] User management
- [ ] Custom alerts
- [ ] WebSocket real-time updates

---

## 📊 Version History

| Version | Date | Status |
|---------|------|--------|
| 2.1.0 | 2026-02-26 | ✅ Current |
| 2.0.0 | 2026-02-16 | ✅ |
| 1.0.0 | 2026-02-03 | ✅ |

---

## 🙏 Acknowledgments

- [OpenCode Smart Model Selector](https://github.com/wuleiyuan/opencode-smart-model-selector) - Companion project
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Chart.js](https://www.chartjs.org/) - Visualization library
