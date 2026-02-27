# Token Monitor 开发记录

## 项目概述

企业版 Token 使用监控系统 - 实时监控 AI API 的 Token 消耗，支持 JWT 认证、限流、缓存、告警和数据导出。

**当前版本**: v2.2.0

---

## 两个项目目录的用途

| 目录 | 用途 |
|------|------|
| `/Users/leiyuanwu/网页小游/token-monitor/` | **本地开发目录** - 包含 index.html 前端开发 |
| `/Users/leiyuanwu/GitHub/token-monitor/` | **GitHub 同步目录** - 发布到 PyPI |

### 工作流程

```
本地目录开发
    ↓
测试、验证
    ↓
同步到 GitHub 目录 + 推送到远程
```

---

## 本次开发内容 (2026-02-27)

### 1. PyPI 自动发布配置

- **问题**: GitHub Actions 使用 API token 方式发布失败
- **解决**: 配置 Trusted Publishing (OIDC)
  - 添加 `id-token: write` 权限
  - 使用 `pypa/gh-action-pypi-publish` action
  - 在 PyPI 项目设置中添加可信发布者

- **验证**: 
  - v2.2.0 Release 成功发布到 PyPI
  - GitHub Actions 工作流正常运行

### 2. 代码审查

| 文件 | 检查项 | 状态 |
|------|--------|------|
| `enterprise_api_server.py` | Python 语法 | ✅ 通过 |
| 所有 .py 文件 | 模块导入 | ✅ 正常 |
| `index.html` | 前端文件存在 | ✅ |
| `pyproject.toml` | 配置文件存在 | ✅ |
| `.github/workflows/release.yml` | Workflow 正确 | ✅ |

### 3. 发布方式确认

最终确定 **只保留标签发布** 模式：

| 触发条件 | 行为 |
|----------|------|
| 推送标签 `v*` | 发布到 PyPI + GitHub Release ✅ |
| 推送分支 | 仅同步代码，不发布 |

**原因**: 小版本更新不需要每次发布到 PyPI，保持版本语义化。

---

## Git 操作记录

### 本次提交

| Commit | 描述 |
|--------|------|
| `d57c8ba` | Revert: only publish on tag push |
| `c4f8a62` | Fix workflow permissions |
| `dd4d1de` | Fix workflow permissions |
| `5076299` | Add GitHub Actions release workflow |

### 发布记录

| 标签 | 日期 | 描述 |
|------|------|------|
| v2.2.0 | 2026-02-27 | Trusted Publishing 配置完成 |
| v2.1.0 | - | 历史版本 |
| v2.0.0 | - | 历史版本 |
| v1.0.0 | - | 历史版本 |

---

## 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| 2.2.0 | 2026-02-27 | PyPI Trusted Publishing 配置完成，自动发布 |
| 2.1.0 | - | 历史版本 |
| 2.0.0 | - | 历史版本 |
| 1.0.0 | - | 初始版本 |

---

## 已知问题

- 暂无单元测试文件

---

## 常用命令

```bash
# 进入 GitHub 目录
cd /Users/leiyuanwu/GitHub/token-monitor

# 测试模块导入
python3 -c "import enterprise_api_server; print('OK')"

# 本地运行
python3 enterprise_api_server.py

# 发布新版本
git tag v2.3.0
git push origin v2.3.0
```

---

*最后更新: 2026-02-27*
