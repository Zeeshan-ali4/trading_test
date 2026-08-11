FROM ghcr.io/astral-sh/uv:0.8-python3.12-bookworm

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-install-project

COPY . .
RUN uv sync

ENV PATH="/app/.venv/bin:${PATH}"
CMD ["quant", "--help"]
