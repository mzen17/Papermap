# ── Stage 1: build the SvelteKit frontend ────────────────────────────────────
FROM oven/bun:1 AS web-builder

WORKDIR /app/web
COPY web/package.json web/bun.lock ./
RUN bun i

COPY web/ ./
RUN bun run build
# outputs to ../fastapi/static per svelte.config.js


# ── Stage 2: run the FastAPI backend ─────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app/fastapi

# install uv
RUN pip install uv --no-cache-dir

COPY fastapi/pyproject.toml fastapi/uv.lock ./
RUN uv sync --frozen --no-dev

COPY fastapi/main.py ./
COPY --from=web-builder /app/fastapi/static ./static

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
