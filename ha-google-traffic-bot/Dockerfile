FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY . /app

# Corregge automaticamente i fine riga (da CRLF di Windows a LF di Linux) e dà i permessi
RUN sed -i -e 's/\r$//' /app/run.sh && chmod +x /app/run.sh

RUN pip install --no-cache-dir requests schedule

CMD [ "/app/run.sh" ]
