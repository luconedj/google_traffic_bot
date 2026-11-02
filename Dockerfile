FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir requests schedule

RUN chmod +x /app/run.sh

CMD [ "/app/run.sh" ]
