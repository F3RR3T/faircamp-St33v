#!/usr/bin/env bash
set -euo pipefail

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Error: ffmpeg is required but not found in PATH." >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 image1.[png|jpg|jpeg] [image2 ...]"
  exit 1
fi

for in_file in "$@"; do
  if [[ ! -f "$in_file" ]]; then
    echo "Skipping (not a file): $in_file" >&2
    continue
  fi

  case "${in_file,,}" in
    *.png|*.jpg|*.jpeg) ;;
    *)
      echo "Skipping (unsupported extension): $in_file" >&2
      continue
      ;;
  esac

  out_file="${in_file%.*}_16x9.jpg"

  ffmpeg -hide_banner -loglevel error -y \
    -i "$in_file" \
    -vf "crop='if(gte(iw/ih,16/9),ih*16/9,iw)':'if(gte(iw/ih,16/9),ih,iw*9/16)'" \
    -q:v 2 \
    "$out_file"

  echo "Wrote: $out_file"
done
