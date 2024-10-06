install:
    uv sync

# TODO: Add a fix command that does auto-fixing
check:
    uv sync --locked
    # TODO: Integrate with editor
    uv run mypy .
    uv run ruff format --check
    uv run ruff check --select "E,F,I"

dev:
    uv run fastapi dev main.py
