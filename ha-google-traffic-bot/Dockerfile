FROM python:3.11-slim

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Installa bash, curl, jq e tutte le dipendenze di sistema di Debian per Chromium
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

COPY . /app

# Converte i fine riga e rende eseguibile run.sh usando bash
RUN sed -i -e 's/\r$//' /app/run.sh && chmod +x /app/run.sh

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir requests schedule playwright

RUN playwright install chromium && \
    chmod -R 777 /ms-playwright

CMD ["/app/run.sh"]
