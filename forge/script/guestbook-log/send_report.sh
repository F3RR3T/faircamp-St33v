#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CONF_FILE="/etc/nginx-digest.conf"
if [[ -f "$CONF_FILE" ]]; then
  # shellcheck source=/etc/nginx-digest.conf
  source "$CONF_FILE"
fi

: "${RECIPIENT:?Set RECIPIENT in /etc/nginx-digest.conf}"
: "${SENDER:?Set SENDER in /etc/nginx-digest.conf}"

REPORT_PATH="$(python3 "$DIR/nginx_digest.py")"
REPORT_DATE="$(basename "$REPORT_PATH" .md)"
SUBJECT_PREFIX="${SUBJECT_PREFIX:-nginx digest}"
SUBJECT="$SUBJECT_PREFIX $REPORT_DATE UTC"

{
  printf 'From: %s\n' "$SENDER"
  printf 'To: %s\n' "$RECIPIENT"
  printf 'Subject: %s\n' "$SUBJECT"
  printf '\n'
  cat "$REPORT_PATH"
} | msmtp -t
