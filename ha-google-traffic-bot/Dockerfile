FROM python:3.11-slim-bookworm

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Solo le librerie di sistema necessarie a Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Playwright + solo headless shell (molto più leggero di Chromium completo)
RUN pip install --no-cache-dir requests "playwright>=1.49" \
    && playwright install chromium-headless-shell \
    && python -c "import playwright, requests; print('deps OK')"

WORKDIR /app
COPY bot.py /app/bot.py

CMD ["python", "/app/bot.py"]
