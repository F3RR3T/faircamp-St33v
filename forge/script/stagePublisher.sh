#!/usr/bin/env bash
# Written by GPT after discussions on how to de-glitch rsync-s to st33v.com
# 31 Jan 2026

set -euo pipefail
source /usr/local/bin/logNotify-lib

ROOT_BUILD="$HOME/dox/st33v.com/faircamp/.faircamp_build/"
SOTD_BUILD="$HOME/dox/st33v.com/sotd/.faircamp_build/"
STAGE="$HOME/dox/st33v.com/stage"
REMOTE="st33v@st33v.com:/srv/www/st33v.com/"  

# rm -rf "$STAGE"
# mkdir -p "$STAGE/sotd"

# materialize staging tree (real files)
rsync -a --delete "$ROOT_BUILD" "$STAGE/"
rsync -a --delete "$SOTD_BUILD" "$STAGE/sotd/"

# generate robots/sitemap in the staged output
gen-robots-sitemap.sh "$STAGE" "https://st33v.com"

# publish atomically
log "Starting rsync stage → st33v.com"
rsync -a --delete "$STAGE/"/ "$REMOTE"

out="$(rsync -aP --delete --stats --human-readable -e 'ssh -p 40022' \
   "$STAGE/"/ "$REMOTE" 2>&1)" || die "rsync failed"
summary="$(printf '%s\n' "$out" | awk '/sent .* bytes/ || /Total transferred file size:/ || /Number of deleted files:/ {print}')"
log "rsync summary: $(printf '%s' "$summary" | paste -sd ' | ' -)"

