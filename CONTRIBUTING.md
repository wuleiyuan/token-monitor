# 🤝 Contributing to Token Monitor

Thank you for your interest in contributing to Token Monitor!

## 📋 Code of Conduct

By participating in this project, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## 🚀 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported
2. Create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details

### Suggesting Features

1. Check existing issues and discussions
2. Create a feature request with:
   - Clear description
   - Use cases
   - Proposed solution (optional)

### Pull Requests

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/token-monitor.git
   ```

3. **Create** a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make** your changes

5. **Test** your changes:
   ```bash
   python -m pytest tests/
   ```

6. **Commit** with clear messages:
   ```bash
   git commit -m "feat: add new feature"
   git commit -m "fix: resolve issue #123"
   ```

7. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create** a Pull Request

## 📝 Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Code style |
| `refactor` | Code refactoring |
| `test` | Tests |
| `chore` | Maintenance |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=. --cov-report=html
```

## 📦 Package Requirements

- Python 3.8+
- FastAPI
- See `requirements.txt` for full list

## 🎯 Pull Request Guidelines

- [ ] Code follows project style
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts

## 💬 Getting Help

- GitHub Discussions
- GitHub Issues
- Read the [Wiki](https://github.com/wuleiyuan/token-monitor/wiki)

---

⭐ Thank you for contributing!
