FROM python:3.11-slim

# Forza Playwright a usare una cartella globale fissa
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Installa tutte le dipendenze di sistema Debian indispensabili per Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Copia i file dell'add-on
COPY . /app

# Corregge i fine riga di run.sh e assegna i permessi di esecuzione
RUN sed -i -e 's/\r$//' /app/run.sh && chmod +x /app/run.sh

# Aggiorna pip e installa le librerie Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir requests schedule playwright

# Installa Chromium e sblocca i permessi globali
RUN playwright install chromium && \
    chmod -R 777 /ms-playwright

CMD ["/app/run.sh"]
