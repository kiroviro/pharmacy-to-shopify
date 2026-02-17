# Contributing

Thank you for your interest in contributing to the Pharmacy-to-Shopify project!

## Quick Start

**Try the demo first** to understand what the project does:
```bash
python3 scripts/demo.py
```

## Development Setup

### Option 1: Local Development

1. Clone the repository and create a virtual environment:

```bash
git clone https://github.com/kiroviro/pharmacy-to-shopify.git
cd pharmacy-to-shopify
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

3. Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

This will automatically run linting and formatting checks before each commit.

### Option 2: Docker Development

```bash
# Build the container
docker-compose build

# Run tests
docker-compose --profile test run test

# Run linter
docker-compose --profile lint run lint

# Run extraction scripts
docker-compose run extractor python scripts/demo.py
```

## Running Tests

```bash
python -m pytest tests/ -v --tb=short
```

With coverage:

```bash
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Linting and Formatting

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

### Check for issues:
```bash
ruff check .
```

### Auto-fix issues:
```bash
ruff check . --fix
```

### Format code:
```bash
ruff format .
```

### Pre-commit hooks:
Pre-commit hooks will automatically run ruff on staged files:
```bash
# Run manually on all files
pre-commit run --all-files

# Run on staged files only (happens automatically on commit)
git commit
```

## Code Style

- **Python 3.9+** — use `from __future__ import annotations` and modern type hints (`list[str]`, `dict[str, int]`, `X | None`)
- **Logging** — use `logger` for progress/status/errors; use `print()` only for user-facing reports and summaries
- **Config** — YAML files in `config/`; loaded via `src/common/config_loader.py`
- Keep functions focused and avoid over-engineering

## Submitting Changes

### Before submitting a Pull Request:

1. **Run tests locally**:
   ```bash
   pytest tests/ -v
   ```

2. **Check linting**:
   ```bash
   ruff check .
   pre-commit run --all-files
   ```

3. **Update documentation** if you've added features or changed behavior

4. **Write clear commit messages**:
   - Use present tense ("Add feature" not "Added feature")
   - Reference issues when applicable (#123)
   - Keep first line under 72 characters

### Pull Request Process

1. Fork the repository and create a branch from `main`
2. Make your changes following the code style guidelines
3. Add tests for new functionality
4. Ensure all tests pass and linting is clean
5. Update documentation as needed
6. Submit a pull request using the provided template

The PR template will guide you through describing:
- What changes you made
- Why you made them
- How to test them
- Any breaking changes

## Reporting Issues

Use the provided issue templates:

- **Bug Report**: For reporting bugs or unexpected behavior
- **Feature Request**: For suggesting new features or improvements

Please search existing issues before creating a new one to avoid duplicates.

## Development Guidelines

### Adding New Sites

See [docs/configuration.md](docs/configuration.md) for how to add support for new pharmacy websites.

### Code Quality

- Write tests for new features
- Keep functions small and focused (< 50 lines when possible)
- Use type hints for function signatures
- Add docstrings for public APIs
- Avoid over-engineering - solve the current problem, not future hypotheticals

### Documentation

- Update relevant docs in `docs/` directory
- Add examples for new features
- Keep README up-to-date
- Document configuration options in `config/` YAML files

## CI/CD

GitHub Actions runs lint + tests on Python 3.9, 3.11, and 3.13 for every push and PR against `main`/`master`.

All checks must pass before merging:
- ✅ Linting (ruff)
- ✅ Tests (pytest)
- ✅ Python 3.9, 3.11, 3.13 compatibility

## Questions?

Feel free to open an issue for questions or join discussions in existing issues.
