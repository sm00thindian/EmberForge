FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY emberforge ./emberforge
COPY personas ./personas
COPY prompts ./prompts
COPY device ./device

RUN pip install --no-cache-dir .

ENV EMBER_HOST=0.0.0.0
ENV EMBER_BACKEND_PORT=8000
ENV EMBERFORGE_ROOT=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["emberforge", "serve", "--host", "0.0.0.0", "--port", "8000"]