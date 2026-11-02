FROM python:3.11-slim

WORKDIR /app

# Installa solo le librerie di sistema essenziali per Chromium e pulisce la cache APT
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copia i file dell'add-on
COPY . /app

# Installa le librerie Python senza memorizzare cache di pip
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir requests schedule playwright

# Installa SOLO Chromium (senza installare Firefox o WebKit) e pulisce i residui di build
RUN playwright install chromium

CMD ["python3", "/app/bot.py"]
