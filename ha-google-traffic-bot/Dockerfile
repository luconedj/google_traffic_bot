FROM python:3.11-slim

# Forza Playwright a usare una cartella globale fissa
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Installa tutte le dipendenze di sistema Debian indispensabili per Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    jq \
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
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copia i file dell'add-on (bot.py, config.yaml, ecc.)
COPY . /app

# CREA RUN.SH DIRETTAMENTE NEL DOCKERFILE (Garantisce che esista e sia in formato Linux LF)
RUN echo '#!/bin/bash' > /app/run.sh && \
    echo 'echo "=== Avvio Add-on Google Maps Traffic Bot ==="' >> /app/run.sh && \
    echo 'export ORIGIN=$(jq --raw-output ".origin // empty" /data/options.json)' >> /app/run.sh && \
    echo 'export DESTINATION=$(jq --raw-output ".destination // empty" /data/options.json)' >> /app/run.sh && \
    echo 'export CHECK_INTERVAL_MINUTES=$(jq --raw-output ".check_interval_minutes // 10" /data/options.json)' >> /app/run.sh && \
    echo 'export DIFF_THRESHOLD_MINUTES=$(jq --raw-output ".diff_threshold_minutes // 5" /data/options.json)' >> /app/run.sh && \
    echo 'export FREE_TRAFFIC_THRESHOLD_MINUTES=$(jq --raw-output ".free_traffic_threshold_minutes // 35" /data/options.json)' >> /app/run.sh && \
    echo 'export ENABLE_TELEGRAM=$(jq --raw-output ".enable_telegram // false" /data/options.json)' >> /app/run.sh && \
    echo 'export TELEGRAM_BOT_TOKEN=$(jq --raw-output ".telegram_bot_token // empty" /data/options.json)' >> /app/run.sh && \
    echo 'export TELEGRAM_CHAT_ID=$(jq --raw-output ".telegram_chat_id // empty" /data/options.json)' >> /app/run.sh && \
    echo 'exec python3 /app/bot.py' >> /app/run.sh && \
    chmod +x /app/run.sh

# Aggiorna pip e installa le librerie Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir requests schedule playwright

# Installa Chromium e sblocca i permessi globali
RUN playwright install chromium && \
    chmod -R 777 /ms-playwright

CMD ["/app/run.sh"]
