FROM python:3.11-slim-bookworm

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends bash jq \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir requests schedule playwright \
    && playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright

COPY . /app
# ...il tuo blocco RUN che crea run.sh resta uguale...

CMD ["/app/run.sh"]
