#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/dox/st33v.com"
OUT="$ROOT/forge/out"
SOTD="$ROOT/sotd"

log() { printf '[sotd-publish] %s\n' "$*" >&2; }
die() { log "$*"; exit 1; }

publish_marker="$OUT/PUBLISH"
[[ -f "$publish_marker" ]] || die "No publish marker: $publish_marker"

# mkdir -p "$SOTD"

# Find candidate release directories in OUT (ignore marker files)
release_dirs=()
for d in "$OUT"/*; do
  [[ -d "$d" ]] || continue
  release_dirs+=( "$d" )
done

[[ ${#release_dirs[@]} -eq 1 ]] || die "Expected exactly 1 release dir in $OUT, found ${#release_dirs[@]}"

rel="${release_dirs[0]}"

[[ -f "$rel/release.eno" ]] || die "Missing release.eno in $(basename "$rel")"

shopt -s nullglob
wav_files=( "$rel"/*.wav )
shopt -u nullglob
(( ${#wav_files[@]} > 0 )) || die "Missing .wav in $(basename "$rel")"

dest="$SOTD/$(basename "$rel")"
[[ ! -e "$dest" ]] || die "Destination already exists: $dest"

mv "$rel" "$dest"
log "Published: $dest"

# Cleanup markers after successful publish
rm -f "$OUT/PUBLISH" "$OUT/BUILT"

