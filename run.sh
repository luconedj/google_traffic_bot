#!/usr/bin/with-contenv bash

echo "=== Avvio Add-on Google Maps Traffic Bot ==="

export ORIGIN=$(jq --raw-output '.origin' /data/options.json)
export DESTINATION=$(jq --raw-output '.destination' /data/options.json)
export CHECK_INTERVAL_MINUTES=$(jq --raw-output '.check_interval_minutes' /data/options.json)
export DIFF_THRESHOLD_MINUTES=$(jq --raw-output '.diff_threshold_minutes' /data/options.json)
export FREE_TRAFFIC_THRESHOLD_MINUTES=$(jq --raw-output '.free_traffic_threshold_minutes' /data/options.json)
export TELEGRAM_BOT_TOKEN=$(jq --raw-output '.telegram_bot_token' /data/options.json)
export TELEGRAM_CHAT_ID=$(jq --raw-output '.telegram_chat_id' /data/options.json)

python3 /app/bot.py
