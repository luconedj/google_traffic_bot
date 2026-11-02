#!/bin/bash
echo "=== Avvio Add-on Google Maps Traffic Bot ==="

export ORIGIN=$(jq --raw-output '.origin // empty' /data/options.json)
export DESTINATION=$(jq --raw-output '.destination // empty' /data/options.json)
export CHECK_INTERVAL_MINUTES=$(jq --raw-output '.check_interval_minutes // 10' /data/options.json)
export DIFF_THRESHOLD_MINUTES=$(jq --raw-output '.diff_threshold_minutes // 5' /data/options.json)
export FREE_TRAFFIC_THRESHOLD_MINUTES=$(jq --raw-output '.free_traffic_threshold_minutes // 35' /data/options.json)
export ENABLE_TELEGRAM=$(jq --raw-output '.enable_telegram // false' /data/options.json)
export TELEGRAM_BOT_TOKEN=$(jq --raw-output '.telegram_bot_token // empty' /data/options.json)
export TELEGRAM_CHAT_ID=$(jq --raw-output '.telegram_chat_id // empty' /data/options.json)

exec python3 /app/bot.py
