#!/usr/bin/env bash
set -euo pipefail
source /usr/local/bin/logNotify-lib

ROOT="$HOME/dox/st33v.com"
OUT="$ROOT/forge/out"
TEMPLATE="$ROOT/forge/template"
SOTD="$ROOT/sotd"

publish_marker="$OUT/PUBLISH"
consume_marker="$OUT/PUBLISHING"

if [[ -f "$consume_marker" ]]; then
  log "Publish already in progress, exiting."
  exit 0
fi

if [[ -f "$publish_marker" ]]; then
  mv "$publish_marker" "$consume_marker"
else
  log "No PUBLISH marker, nothing to do."
  exit 0
fi

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
audio_files=( "$rel"/*.flac "$rel"/*.wav )
shopt -u nullglob
(( ${#audio_files[@]} > 0 )) || die "Missing audio file (.flac or .wav) in $(basename "$rel")"

dest="$SOTD/$(basename "$rel")"
[[ ! -e "$dest" ]] || die "Destination already exists: $dest"

mv "$rel" "$dest"
log "Published: $dest"

# Cleanup markers after successful publish
rm $OUT/BUILT
rm $TEMPLATE/lyrics $TEMPLATE/title
trap 'rm -f "$consume_marker"' EXIT
