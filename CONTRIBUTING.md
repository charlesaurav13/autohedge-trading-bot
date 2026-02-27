# Contributing to AutoHedge

Thank you for considering contributing to AutoHedge! 🎉

## 🤝 How to Contribute

### Reporting Issues

- **Search existing issues** first to avoid duplicates
- **Use issue templates** when available
- **Provide details**: OS, Python version, error messages, logs
- **Include steps to reproduce** the problem

### Suggesting Features

- **Check roadmap** in README.md first
- **Describe the use case** clearly
- **Consider impact** on existing functionality
- **Be open to discussion** on implementation

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly** (see Testing section)
5. **Commit with clear messages** (see Commit Guidelines)
6. **Push to your fork**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

---

## 📋 Development Setup

### Prerequisites

- Python 3.10+
- Git
- Virtual environment tools

### Setup Steps

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/AutoHedge.git
cd AutoHedge

# 2. Set up environment
./setup_training.sh
source training_env/bin/activate

# 3. Install dev dependencies
pip install -r requirements_dev.txt

# 4. Configure pre-commit hooks (if using)
pre-commit install

# 5. Copy environment template
cp .env.example .env
# Edit .env with test credentials
```

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_trading_bot.py

# With coverage
pytest --cov=autohedge --cov-report=html
```

### Manual Testing

```bash
# Test model wrapper
python trained_model_wrapper.py

# Test paper trading
python paper_trading.py --test

# Test AutoHedge
cd autohedge && python main.py --test

# Dry run training pipeline
python training_pipeline.py --mode initial --timesteps 1000  # Quick test
```

---

## 📝 Code Style

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Imports**: Use `isort` for organizing
- **Formatting**: Use `black` for auto-formatting
- **Type hints**: Encouraged for new code

### Formatting Tools

```bash
# Format code
black .

# Sort imports
isort .

# Type checking
mypy main_trading_loop.py

# Linting
flake8 --max-line-length=100
```

### Pre-commit Hook (Optional)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
```

---

## 📋 Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples

```bash
# Good commits
git commit -m "feat(trading): Add support for ETH trading"
git commit -m "fix(rl): Resolve overtraining in Phase 2"
git commit -m "docs(readme): Update installation instructions"

# Bad commits (avoid)
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "updates"
```

---

## 🏗️ Architecture Guidelines

### When Adding Features

**Consider:**
- Impact on existing functionality
- Performance implications (especially for trading loop)
- Security implications (API keys, trading decisions)
- Testing requirements
- Documentation needs

**File organization:**
- Core trading logic → `trading_bot.py`
- Training pipeline → `training_pipeline.py`
- Integration → `trained_model_wrapper.py`
- Config → `config/training_config.yaml`
- Docs → Markdown files

### Code Structure

```python
# Good: Clear, documented, testable
def calculate_position_size(
    balance: float,
    risk_percent: float,
    leverage: int
) -> float:
    """
    Calculate position size with risk management.
    
    Args:
        balance: Current account balance
        risk_percent: Risk percentage (e.g., 0.4 for 40%)
        leverage: Trading leverage
    
    Returns:
        Position size in USDT
    """
    return balance * risk_percent * leverage

# Bad: Unclear, undocumented, hardcoded
def calc(x, y, z):
    return x * y * z * 10
```

---

## 🔐 Security

### API Keys & Secrets

- **Never commit** `.env` or API keys
- **Use `.env.example`** for templates
- **Check .gitignore** before committing
- **Rotate keys** if accidentally committed

### Trading Safety

- **Test in paper trading** first
- **Start with small amounts** in live
- **Add safety checks** for new features
- **Document risks** clearly

---

## 📚 Documentation

### When to Update Docs

- **New features**: Add to README.md and relevant guides
- **Config changes**: Update `config/training_config.yaml` comments
- **API changes**: Update MODEL_INTEGRATION.md
- **Breaking changes**: Add to CHANGELOG.md (create if doesn't exist)

### Documentation Files

- **README.md**: Overview, quick start, features
- **PRODUCTION_SYSTEM.md**: Training system guide
- **MODEL_INTEGRATION.md**: Integration architecture
- **CONTRIBUTING.md**: This file
- **Code comments**: For complex logic

---

## 🎯 Priority Areas

We especially welcome contributions in:

1. **Testing**: More test coverage
2. **Documentation**: Improved guides, tutorials
3. **Performance**: Optimization for training/inference
4. **Features**: See roadmap in README.md
5. **Bug fixes**: Check open issues

---

## 🚫 What Not to Contribute

Please avoid:

- **Untested code**: All new features need tests
- **Breaking changes** without discussion
- **Large refactors** without prior agreement
- **New dependencies** without justification
- **Trading strategies** without validation

---

## 💬 Communication

- **GitHub Issues**: Bug reports, feature requests
- **Pull Requests**: Code contributions
- **Discussions**: General questions, ideas
- **Email**: security@example.com (for security issues only)

---

## 📜 Code of Conduct

### Our Pledge

- Be respectful and inclusive
- Welcome diverse perspectives
- Focus on constructive feedback
- Help newcomers learn

### Unacceptable Behavior

- Harassment, discrimination, trolling
- Spam, self-promotion without context
- Sharing private information
- Disruptive behavior

### Reporting

If you experience or witness unacceptable behavior, please report to:
- **Email**: conduct@example.com
- **GitHub**: Report via issue or contact repository owner

---

## ✅ Checklist Before Submitting PR

- [ ] Code follows style guide (black + isort)
- [ ] Tests added/updated and passing
- [ ] Documentation updated if needed
- [ ] Commit messages follow guidelines
- [ ] No secrets or API keys committed
- [ ] Changes tested in paper trading
- [ ] PR description explains changes clearly

---

## 🙏 Thank You!

Every contribution helps make AutoHedge better. Whether it's:
- Reporting a bug 🐛
- Suggesting a feature 💡
- Improving docs 📚
- Writing code 💻
- Helping others 🤝

**You're making a difference!** ❤️

---

## 📖 Additional Resources

- **README.md**: Project overview
- **PRODUCTION_SYSTEM.md**: Training guide
- **MODEL_INTEGRATION.md**: Integration architecture
- **Issues**: https://github.com/charlesaurav13/AutoHedge/issues

---

_Questions? Open an issue or start a discussion!_
