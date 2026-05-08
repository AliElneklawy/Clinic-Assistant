# ======================== Build Stage ======================== 

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen  # Installs deps in .venv folder

# ======================== Runtime Stage ======================== 

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

RUN useradd -m appuser

USER appuser

CMD ["python", "-m", "src.cli"]