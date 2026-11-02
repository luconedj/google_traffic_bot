FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY . /app

# Installa esplicitamente playwright, requests e schedule
RUN pip install --no-cache-dir playwright requests schedule

# Installa i binari del browser Chromium necessari per lo scraping
RUN playwright install chromium

CMD ["python3", "/app/bot.py"]
