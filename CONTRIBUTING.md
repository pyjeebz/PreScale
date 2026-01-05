# Contributing to Helios

Thank you for your interest in contributing to Helios! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@helios.dev](mailto:conduct@helios.dev).

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Kubernetes cluster (local: minikube, kind, or Docker Desktop)
- Helm 3.x
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/helios.git
   cd helios
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/helios-platform/helios.git
   ```

## Development Setup

### 1. Create Virtual Environment

```bash
# Linux/macOS
python -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install -r ml/requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Run Tests

```bash
pytest tests/ -v
```

### 5. Start Local Services

```bash
# Using Docker Compose
docker-compose up -d

# Or deploy to local Kubernetes
helm install helios ./charts/helios --namespace helios --create-namespace
```

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, Kubernetes version)
- **Logs and error messages** (sanitized of sensitive data)
- **Screenshots** if applicable

Use the bug report template when opening an issue.

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:

- **Use case** - Why is this enhancement needed?
- **Proposed solution** - How should it work?
- **Alternatives considered** - What other approaches did you consider?
- **Additional context** - Any other relevant information

### Contributing Code

1. **Find an issue** to work on, or create one for discussion
2. **Comment on the issue** to let others know you're working on it
3. **Create a branch** from `main` for your work
4. **Make your changes** following our coding standards
5. **Write/update tests** for your changes
6. **Submit a pull request**

#### Good First Issues

Look for issues labeled `good first issue` - these are specifically curated for new contributors.

## Pull Request Process

### Before Submitting

- [ ] Code follows the project's coding standards
- [ ] All tests pass locally (`pytest tests/ -v`)
- [ ] Linting passes (`ruff check .`)
- [ ] Type checking passes (`mypy ml/`)
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventions

### PR Guidelines

1. **Title**: Use a clear, descriptive title
   - `feat: Add anomaly detection for disk I/O`
   - `fix: Resolve memory leak in prediction service`
   - `docs: Update deployment guide`

2. **Description**: Fill out the PR template completely
   - What changes were made?
   - Why were they made?
   - How to test them?

3. **Size**: Keep PRs focused and reasonably sized
   - Large changes should be split into smaller PRs
   - Each PR should do one thing well

### Review Process

1. Automated checks must pass (CI/CD, tests, linting)
2. At least one maintainer approval required
3. Address review feedback promptly
4. Squash commits if requested before merge

## Coding Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with these tools:

```bash
# Formatting
ruff format .

# Linting
ruff check .

# Type checking
mypy ml/ --strict
```

### Code Organization

```
ml/
├── inference/          # Prediction API service
│   ├── main.py        # FastAPI application
│   ├── models.py      # Pydantic models
│   └── predictors.py  # Prediction logic
├── pipeline/          # Training pipeline
├── models/            # Saved ML models
└── cost_intelligence/ # Cost analysis service
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code change that neither fixes nor adds
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### API Design

- Follow RESTful conventions
- Use meaningful HTTP status codes
- Include proper error messages
- Document endpoints with OpenAPI/Swagger

## Testing

### Test Structure

```
tests/
├── unit/              # Unit tests
│   ├── test_predictors.py
│   └── test_models.py
├── integration/       # Integration tests
│   └── test_api.py
└── e2e/              # End-to-end tests
    └── test_workflow.py
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=ml --cov-report=html

# Specific test file
pytest tests/unit/test_predictors.py -v

# By marker
pytest tests/ -m "not slow" -v
```

### Writing Tests

- Use descriptive test names: `test_predict_cpu_returns_valid_forecast`
- Follow Arrange-Act-Assert pattern
- Mock external dependencies
- Test edge cases and error conditions

## Documentation

### Code Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style docstrings:

```python
def predict_cpu(data: pd.DataFrame, horizon: int = 24) -> Dict[str, Any]:
    """Generate CPU usage predictions.

    Args:
        data: Historical CPU metrics with timestamp index.
        horizon: Number of hours to forecast.

    Returns:
        Dictionary containing predictions and confidence intervals.

    Raises:
        ValueError: If data is empty or invalid.
    """
```

### User Documentation

- Update README.md for user-facing changes
- Add/update docs in `docs/` directory
- Include examples for new features

## Community

### Getting Help

- **GitHub Discussions**: Ask questions and share ideas
- **Discord**: Real-time chat with the community
- **Stack Overflow**: Tag questions with `helios-ml`

### Maintainers

Questions about contributing? Reach out to:

- GitHub: [@helios-platform](https://github.com/helios-platform)
- Email: [maintainers@helios.dev](mailto:maintainers@helios.dev)

### Recognition

Contributors are recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Release notes
- Project documentation

---

## License

By contributing to Helios, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

Thank you for contributing to Helios! 🚀
