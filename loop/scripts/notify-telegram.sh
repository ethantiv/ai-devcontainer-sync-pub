#!/bin/bash

# Telegram notification for loop completion
# Requires: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode) MODE="$2"; shift 2 ;;
        --iterations) ITERATIONS="$2"; shift 2 ;;
        --total) TOTAL="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        --status) STATUS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check required env vars
if [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]]; then
    echo "[NOTIFY] Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)"
    exit 0
fi

# Format duration (seconds -> Xm Ys)
format_duration() {
    local seconds=$1
    local minutes=$((seconds / 60))
    local secs=$((seconds % 60))
    if [[ $minutes -gt 0 ]]; then
        echo "${minutes}m ${secs}s"
    else
        echo "${secs}s"
    fi
}

# Map status to emoji and text
case $STATUS in
    success) STATUS_EMOJI="✅"; STATUS_TEXT="Sukces" ;;
    completed) STATUS_EMOJI="✔️"; STATUS_TEXT="Ukończono iteracje" ;;
    interrupted) STATUS_EMOJI="⚠️"; STATUS_TEXT="Przerwane" ;;
    *) STATUS_EMOJI="❓"; STATUS_TEXT="Nieznany" ;;
esac

# Map mode to icon
case $MODE in
    build) MODE_ICON="🔨" ;;
    plan) MODE_ICON="📋" ;;
    *) MODE_ICON="🔄" ;;
esac

# Get project name
PROJECT=$(basename "$(pwd)")

# Build message
MESSAGE="${MODE_ICON} *Zadanie zakończone*

Tryb: ${MODE}
Status: ${STATUS_EMOJI} ${STATUS_TEXT}
Iteracje: ${ITERATIONS}/${TOTAL}
Czas: $(format_duration "$DURATION")
Projekt: ${PROJECT}"

# Send to Telegram
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" \
    -d text="$MESSAGE" \
    -d parse_mode="Markdown" > /dev/null

echo "[NOTIFY] Telegram notification sent"
