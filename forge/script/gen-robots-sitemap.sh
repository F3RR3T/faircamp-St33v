#!/usr/bin/env bash
set -euo pipefail
source /usr/local/bin/logNotify-lib

include_media=0
positional=()
while (( $# )); do
  case "$1" in
    --include-media) include_media=1; shift ;;
    --) shift; while (( $# )); do positional+=("$1"); shift; done ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *) positional+=("$1"); shift ;;
  esac
done
set -- "${positional[@]+"${positional[@]}"}"

OUT_DIR="${1:-.faircamp_build}"
SITE_URL="${2:-https://st33v.com}"

cd "$OUT_DIR"

STATE_FILE=".sitemap-state.tsv"

# --- robots.txt ---
cat > robots.txt <<EOF
User-agent: *
Allow: /

Sitemap: ${SITE_URL%/}/sitemap.xml
EOF

# --- sitemap.xml ---
tmp="$(mktemp)"
new_state="$(mktemp)"

declare -A prev_hashes=()
declare -A prev_lastmods=()

if [[ -f "$STATE_FILE" ]]; then
  while IFS=$'\t' read -r path hash lastmod; do
    [[ -n "${path:-}" && -n "${hash:-}" && -n "${lastmod:-}" ]] || continue
    prev_hashes["$path"]="$hash"
    prev_lastmods["$path"]="$lastmod"
  done < "$STATE_FILE"
fi

# R2 prep: identify single-track releases — any dir (at any depth) whose
# direct numeric subdirs count to exactly 1. Track pages of these are
# dropped as duplicates of the release page, which carries the lyrics.
declare -A single_track_release=()
declare -A _numeric_subdir_count=()
while IFS= read -r -d '' nd; do
  parent="$(dirname "$nd")"
  parent="${parent#./}"
  _numeric_subdir_count["$parent"]=$(( ${_numeric_subdir_count["$parent"]:-0} + 1 ))
done < <(find . -type d -regextype posix-extended -regex '.*/[0-9]+' -print0)
for parent in "${!_numeric_subdir_count[@]}"; do
  (( _numeric_subdir_count["$parent"] == 1 )) && single_track_release["$parent"]=1
done

# R3: by default index HTML/PDF only; --include-media restores audio assets.
if (( include_media )); then
  find_types=( -name '*.html' -o -name '*.pdf' \
               -o -name '*.mp3' -o -name '*.flac' -o -name '*.opus' )
else
  find_types=( -name '*.html' -o -name '*.pdf' )
fi

scanned=0
kept=0

while IFS= read -r -d '' f; do
  scanned=$((scanned + 1))
  path="${f#./}"

  # R3: drop anything under a downloads/ subtree (asset bundles).
  if (( ! include_media )) && [[ "$path" == *"/downloads/"* || "$path" == downloads/* ]]; then
    continue
  fi

  # R2: drop single-track-release track pages (the "double jump").
  if [[ "$path" =~ ^(.+)/([0-9]+)/index\.html$ ]]; then
    rel="${BASH_REMATCH[1]}"
    if [[ -n "${single_track_release[$rel]:-}" ]]; then
      continue
    fi
  fi

  checksum="$(sha256sum "$f" | awk '{print $1}')"

  if [[ "${prev_hashes[$path]:-}" == "$checksum" ]]; then
    lastmod="${prev_lastmods[$path]}"
  else
    lastmod="$(date -u -r "$f" +%Y-%m-%dT%H:%M:%SZ)"
  fi

  printf '%s\t%s\t%s\n' "$path" "$lastmod" "$checksum" >> "$tmp"
  kept=$((kept + 1))
done < <(find . -type f \( "${find_types[@]}" \) \
  ! -path './.git/*' ! -path './assets/*' ! -path './static/*' \
  ! -path "./$STATE_FILE" ! -path './robots.txt' ! -path './sitemap.xml' \
  -print0 | sort -z)

{
  printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>'
  printf '%s\n' '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
  while IFS=$'\t' read -r path lastmod checksum; do
    url="${SITE_URL%/}/$(printf '%s' "$path" | sed 's/&/\&amp;/g')"
    printf '  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n' "$url" "$lastmod"
    printf '%s\t%s\t%s\n' "$path" "$checksum" "$lastmod" >> "$new_state"
  done < "$tmp"
  printf '%s\n' '</urlset>'
} > sitemap.xml

mv "$new_state" "$STATE_FILE"
rm -f "$tmp"

log "Wrote: $OUT_DIR/sitemap.xml (scanned=$scanned kept=$kept include_media=$include_media)"
