FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PULSE_HOST=0.0.0.0 \
    PULSE_RELOAD=0 \
    PULSE_PORT=8765

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

EXPOSE 8765

CMD ["sh", "-c", "uv run uvicorn us_market_pulse.app:app --host 0.0.0.0 --port ${PORT:-${PULSE_PORT:-8765}}"]
