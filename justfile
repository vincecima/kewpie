install:
    uv sync

check:
    uv sync --locked
    uv run mypy .
    uv run ruff check .

dev:
    uv run fastapi dev main.py
