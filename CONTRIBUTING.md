# Contributing

## Development Setup

1. Clone the repository and create a virtual environment:

```bash
git clone https://github.com/kiril/webcrawler-shopify.git
cd webcrawler-shopify
python -m venv venv
source venv/bin/activate
```

2. Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest tests/ -v --tb=short
```

With coverage:

```bash
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Linting

This project uses [ruff](https://docs.astral.sh/ruff/) for linting:

```bash
ruff check src/ tests/
```

## Code Style

- **Python 3.9+** — use `from __future__ import annotations` and modern type hints (`list[str]`, `dict[str, int]`, `X | None`)
- **Logging** — use `logger` for progress/status/errors; use `print()` only for user-facing reports and summaries
- **Config** — YAML files in `config/`; loaded via `src/common/config_loader.py`
- Keep functions focused and avoid over-engineering

## CI

GitHub Actions runs lint + tests on Python 3.9, 3.11, and 3.13 for every push and PR against `main`/`master`.
