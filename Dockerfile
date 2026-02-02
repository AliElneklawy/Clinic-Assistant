FROM python:3.13.5-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

COPY src/ .

CMD ["uv", "run", ".\src\tg_bot.py"]