FROM python:3.11-slim-bookworm

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends bash jq \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir requests schedule playwright \
    && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright \
    && python -c "import playwright, requests, schedule; print('deps OK')"

COPY bot.py /app/bot.py

CMD ["python", "/app/bot.py"]