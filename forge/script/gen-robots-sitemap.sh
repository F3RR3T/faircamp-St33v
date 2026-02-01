#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-.faircamp_build}"
SITE_URL="${2:-https://st33v.com}"

cd "$OUT_DIR"

# --- robots.txt ---
cat > robots.txt <<EOF
User-agent: *
Allow: /

Sitemap: ${SITE_URL%/}/sitemap.xml
EOF

# --- sitemap.xml ---
# Include HTML pages + common content types; exclude obvious junk.
# If you have multiple languages/hosts, we can expand later.
tmp="$(mktemp)"
find . -type f \( -name '*.html' -o -name '*.pdf' -o -name '*.mp3' -o -name '*.flac' \) \
  ! -path './.git/*' ! -path './assets/*' ! -path './static/*' \
  -print0 \
| sort -z \
| while IFS= read -r -d '' f; do
    # Turn ./path/index.html into /path/index.html
    path="${f#./}"
    # Basic lastmod (UTC) from file mtime
    lastmod="$(date -u -r "$f" +%Y-%m-%dT%H:%M:%SZ)"
    printf '%s\t%s\n' "$path" "$lastmod"
  done > "$tmp"

{
  printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>'
  printf '%s\n' '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
  while IFS=$'\t' read -r path lastmod; do
    # Escape ampersands minimally
    url="${SITE_URL%/}/$(printf '%s' "$path" | sed 's/&/\&amp;/g')"
    printf '  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n' "$url" "$lastmod"
  done < "$tmp"
  printf '%s\n' '</urlset>'
} > sitemap.xml

rm -f "$tmp"

echo "Wrote: $OUT_DIR/robots.txt"
echo "Wrote: $OUT_DIR/sitemap.xml"

