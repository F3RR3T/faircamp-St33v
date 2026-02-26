#!/usr/bin/env bash
set -euo pipefail

# Dependencies: ffmpeg, ffprobe, python3 (all CLI; no interactive prompts).

usage() {
  cat >&2 <<'USAGE'
Usage:
  master_sotd_audio.sh \
    --input <input.wav> \
    --date <YYYY-MM-DD> \
    --output <output.flac> \
    --title-file <template/title> \
    --archive-dir <forge/rawAudio>
USAGE
  exit 2
}

log() {
  printf '[sotd-master] %s\n' "$*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf '[sotd-master] Missing required command: %s\n' "$1" >&2
    exit 2
  }
}

parse_loudnorm_json() {
  local log_path="$1"
  local key="$2"
  python3 - "$log_path" "$key" <<'PY'
import json
import re
import sys

path, key = sys.argv[1], sys.argv[2]
text = open(path, 'r', encoding='utf-8', errors='ignore').read()
blocks = re.findall(r'\{[\s\S]*?\}', text)
for b in reversed(blocks):
    try:
        data = json.loads(b)
    except Exception:
        continue
    if key in data:
        print(data[key])
        raise SystemExit(0)
raise SystemExit(1)
PY
}

INPUT=""
DATE_ISO=""
OUTPUT=""
TITLE_FILE=""
ARCHIVE_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="${2:-}"; shift 2 ;;
    --date) DATE_ISO="${2:-}"; shift 2 ;;
    --output) OUTPUT="${2:-}"; shift 2 ;;
    --title-file) TITLE_FILE="${2:-}"; shift 2 ;;
    --archive-dir) ARCHIVE_DIR="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *)
      printf '[sotd-master] Unknown argument: %s\n' "$1" >&2
      usage
      ;;
  esac
done

[[ -n "$INPUT" && -n "$DATE_ISO" && -n "$OUTPUT" && -n "$TITLE_FILE" && -n "$ARCHIVE_DIR" ]] || usage
[[ -f "$INPUT" ]] || { printf '[sotd-master] Input WAV not found: %s\n' "$INPUT" >&2; exit 2; }
[[ -f "$TITLE_FILE" ]] || { printf '[sotd-master] title file not found: %s\n' "$TITLE_FILE" >&2; exit 2; }
[[ "$DATE_ISO" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { printf '[sotd-master] Invalid --date (expected YYYY-MM-DD): %s\n' "$DATE_ISO" >&2; exit 2; }

require_cmd ffmpeg
require_cmd ffprobe
require_cmd python3

mkdir -p "$(dirname "$OUTPUT")"
mkdir -p "$ARCHIVE_DIR"

if [[ -e "$OUTPUT" ]]; then
  printf '[sotd-master] Refusing to overwrite existing mastered output: %s\n' "$OUTPUT" >&2
  exit 3
fi

TITLE="$(python3 - "$TITLE_FILE" <<'PY'
import sys
p = sys.argv[1]
with open(p, 'r', encoding='utf-8') as f:
    s = f.read().rstrip('\r\n')
print(s)
PY
)"

COMMENT="SOTD $DATE_ISO | Licence: CC BY-NC-SA 4.0"
TP_CEILING_DBTP="-1.5"
TP_CEILING_LINEAR="0.84"

# Light, repeatable chain: HPF (~50 Hz), gentle compression, then limiting and loudness normalization.
PREMASTER_CHAIN="highpass=f=50,acompressor=threshold=-18dB:ratio=1.8:attack=20:release=180,alimiter=limit=${TP_CEILING_LINEAR}:level=false"

log "Paths: input=$INPUT | output=$OUTPUT"
log "Metadata: title=$TITLE | album=Song of the Day | artist=St33v™ | comment=$COMMENT | tp_ceiling=${TP_CEILING_DBTP} dBTP"

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ANALYSIS_LOG="$TMP_DIR/pass1.log"
if ! ffmpeg -nostdin -hide_banner -v info \
  -i "$INPUT" \
  -af "${PREMASTER_CHAIN},loudnorm=I=-12:TP=${TP_CEILING_DBTP}:LRA=7:print_format=json" \
  -f null - > /dev/null 2> "$ANALYSIS_LOG"; then
  printf '[sotd-master] First-pass loudness analysis failed\n' >&2
  exit 1
fi

MEASURED_I="$(parse_loudnorm_json "$ANALYSIS_LOG" "input_i")" || { printf '[sotd-master] Could not parse input_i from loudnorm output\n' >&2; exit 1; }
MEASURED_TP="$(parse_loudnorm_json "$ANALYSIS_LOG" "input_tp")" || { printf '[sotd-master] Could not parse input_tp from loudnorm output\n' >&2; exit 1; }
MEASURED_LRA="$(parse_loudnorm_json "$ANALYSIS_LOG" "input_lra")" || { printf '[sotd-master] Could not parse input_lra from loudnorm output\n' >&2; exit 1; }
MEASURED_THRESH="$(parse_loudnorm_json "$ANALYSIS_LOG" "input_thresh")" || { printf '[sotd-master] Could not parse input_thresh from loudnorm output\n' >&2; exit 1; }
MEASURED_OFFSET="$(parse_loudnorm_json "$ANALYSIS_LOG" "target_offset")" || { printf '[sotd-master] Could not parse target_offset from loudnorm output\n' >&2; exit 1; }

TMP_OUT="$TMP_DIR/mastered.flac"
PASS2_LOG="$TMP_DIR/pass2.log"

if ! ffmpeg -nostdin -hide_banner -v info \
  -i "$INPUT" \
  -af "${PREMASTER_CHAIN},loudnorm=I=-12:TP=${TP_CEILING_DBTP}:LRA=7:linear=true:measured_I=${MEASURED_I}:measured_TP=${MEASURED_TP}:measured_LRA=${MEASURED_LRA}:measured_thresh=${MEASURED_THRESH}:offset=${MEASURED_OFFSET}:print_format=json" \
  -map_metadata -1 \
  -metadata title="$TITLE" \
  -metadata album="Song of the Day" \
  -metadata artist="St33v™" \
  -metadata comment="$COMMENT" \
  -c:a flac -compression_level 8 \
  "$TMP_OUT" > /dev/null 2> "$PASS2_LOG"; then
  printf '[sotd-master] Mastering/encode pass failed\n' >&2
  exit 1
fi

[[ -s "$TMP_OUT" ]] || { printf '[sotd-master] Mastering produced empty output\n' >&2; exit 1; }

POST_I="$(parse_loudnorm_json "$PASS2_LOG" "output_i" || true)"
POST_TP="$(parse_loudnorm_json "$PASS2_LOG" "output_tp" || true)"

mv -- "$TMP_OUT" "$OUTPUT"

archive_target="$ARCHIVE_DIR/$(basename "$INPUT")"
if [[ -e "$archive_target" ]]; then
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  stem="$(basename "$INPUT" .wav)"
  archive_target="$ARCHIVE_DIR/${stem}-${ts}.wav"
fi
mv -- "$INPUT" "$archive_target"

post_i_display="${POST_I:-unavailable}"
post_tp_display="${POST_TP:-unavailable}"
log "Measurements: pre_I=${MEASURED_I} LUFS | pre_TP=${MEASURED_TP} dBTP | post_I=${post_i_display} LUFS | post_TP=${post_tp_display} dBTP"
log "Archived raw WAV to: $archive_target"
