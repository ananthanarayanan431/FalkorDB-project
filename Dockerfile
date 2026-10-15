# Knowledge-transfer API. Build:  docker build -t kt-api .
# Run migrations first:          docker run --env-file .env kt-api alembic upgrade head
# Then the API:                  docker run --env-file .env -p 8000:8000 kt-api

FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.7.19 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY alembic.ini ./
COPY migrations ./migrations
COPY knowledge_transfer ./knowledge_transfer

FROM python:3.14-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"]
# --proxy-headers trusts X-Forwarded-* only from FORWARDED_ALLOW_IPS (default 127.0.0.1);
# set it to your reverse proxy's address. --no-server-header hides the uvicorn banner.
CMD ["uvicorn", "knowledge_transfer.api:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--no-server-header"]
