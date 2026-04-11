#!/usr/bin/env bash
set -euo pipefail
source /usr/local/bin/logNotify-lib

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
# Include HTML pages + common content types; exclude obvious junk.
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

find . -type f \( -name '*.html' -o -name '*.pdf' \
  -o -name '*.mp3' -o -name '*.flac' -o -name '*.opus' \) \
  ! -path './.git/*' ! -path './assets/*' ! -path './static/*' \
  ! -path "./$STATE_FILE" ! -path './robots.txt' ! -path './sitemap.xml' \
  -print0 \
| sort -z \
| while IFS= read -r -d '' f; do
    # Turn ./path/index.html into path/index.html
    path="${f#./}"
    checksum="$(sha256sum "$f" | awk '{print $1}')"

    if [[ "${prev_hashes[$path]:-}" == "$checksum" ]]; then
      lastmod="${prev_lastmods[$path]}"
    else
      lastmod="$(date -u -r "$f" +%Y-%m-%dT%H:%M:%SZ)"
    fi

    printf '%s\t%s\t%s\n' "$path" "$lastmod" "$checksum"
  done > "$tmp"

{
  printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>'
  printf '%s\n' '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
  while IFS=$'\t' read -r path lastmod checksum; do
    # Escape ampersands minimally
    url="${SITE_URL%/}/$(printf '%s' "$path" | sed 's/&/\&amp;/g')"
    printf '  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n' "$url" "$lastmod"
    printf '%s\t%s\t%s\n' "$path" "$checksum" "$lastmod" >> "$new_state"
  done < "$tmp"
  printf '%s\n' '</urlset>'
} > sitemap.xml

mv "$new_state" "$STATE_FILE"
rm -f "$tmp"

#notify "Wrote: $OUT_DIR/robots.txt"
log "Wrote: $OUT_DIR/sitemap.xml"
