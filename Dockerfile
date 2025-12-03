FROM python:3.13-alpine

EXPOSE 8000

# Install package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG APP_DIR=/app
WORKDIR ${APP_DIR}

# Install python dependencies
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=${APP_DIR}/.venv

COPY pyproject.toml .
COPY uv.lock .
COPY README.md .
COPY src src

RUN uv sync \
  --locked

ENV CORDRA_RUN_MODE=http

CMD ["uv", "run", "cordra-mcp"]
