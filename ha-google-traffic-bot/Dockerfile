FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Assicura che pip, setuptools e wheel siano aggiornati
RUN python3 -m pip install --upgrade pip setuptools wheel

# Installa i pacchetti usando esplicitamente il modulo pip del python3 di sistema
RUN python3 -m pip install --no-cache-dir requests schedule playwright

# Installa Chromium e le sue dipendenze di sistema a livello globale
RUN python3 -m playwright install --with-deps chromium

COPY . /app

CMD ["python3", "/app/bot.py"]
