#!/usr/bin/env bash
# Written by GPT after discussions on how to de-glitch rsync-s to st33v.com
# 31 Jan 2026

set -euo pipefail

ROOT_BUILD="$HOME/dox/st33v.com/faircamp/.faircamp_build/"
SOTD_BUILD="$HOME/dox/st33v.com/sotd/.faircamp_build/"
STAGE="$HOME/dox/st33v.com/stage"
REMOTE="st33v@st33v.com:/srv/www/st33v.com/"  

rm -rf "$STAGE"
mkdir -p "$STAGE/sotd"

# materialize staging tree (real files)
rsync -a --delete "$ROOT_BUILD" "$STAGE/"
rsync -a --delete "$SOTD_BUILD" "$STAGE/sotd/"

# generate robots/sitemap in the staged output
gen-robots-sitemap.sh "$STAGE" "https://st33v.com"

# publish atomically
rsync -anv --delete "$STAGE/"/ "$REMOTE"

