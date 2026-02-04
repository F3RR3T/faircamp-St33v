#!/usr/bin/env bash
set -euo pipefail

source /usr/local/bin/logNotify-lib

ROOT="$HOME/dox/st33v.com"
FORGE="$ROOT/forge"
IN="$FORGE/in"
OUT="$FORGE/out"
TPL="$FORGE/template"
shopt -s nullglob
cover_files=( "$TPL"/*.jpg "$TPL"/*.png )
shopt -u nullglob

# die() { echo "[sotd-build] $*" >&2; exit 1; }

# --- sanity checks --------------------------------------------------------

wav=( "$IN"/*.wav )
[[ -e "${wav[0]}" ]] || die "No wav file in forge/in"
[[ ${#wav[@]} -eq 1 ]] || die "More than one wav in forge/in (ambiguous)"
[[ -f "$TPL/title" ]] || die "template/title missing"

template_file="$TPL/release.template"
[[ -f "$template_file" ]] || die "release.template missing"

# --- derive variables -----------------------------------------------------
slugify() {
  local s="$1"
  local ascii

  # Try to transliterate to ASCII; if it fails, keep original
  ascii="$(printf '%s' "$s" | iconv -f UTF-8 -t ASCII//TRANSLIT 2>/dev/null || printf '%s' "$s")"

  printf '%s' "$ascii" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+//g'
}

title="$(cat "$TPL/title")"
date_today="$(date -I)"
slug_title="$(slugify "$title")"
slug="$date_today-$slug_title"

release_dir="$OUT/$slug"
mkdir -p "$release_dir"

has_lyrics=false
lyrics_md=""

if [[ -f "$TPL/lyrics" ]]; then
  has_lyrics=true
  lyrics_md="$(sed 's/$/  /' "$TPL/lyrics")" # add two spaces to force markdown newline
  lyrics_md="${lyrics_md//$'\r'/}"   # strip windows CR if present
fi

# synopsis: first ~3 lines, <256 chars, joined by " / "
synopsis=""
if $has_lyrics; then
  synopsis="$(head -n 3 <<< "$lyrics_md" \
    | tr '\n' '/' \
    | sed 's|/| / |g' \
    | cut -c1-255)"
fi

if (( ${#cover_files[@]} == 0 )); then
  log "No cover image found in template/"
elif (( ${#cover_files[@]} > 1 )); then
  die "Multiple cover images found in template/: ${cover_files[*]}"
fi
coverArtFile="$(basename "${cover_files[0]}")"
log "cover art filename is $coverArtFile"
cover_desc=$(printf 'Cover image, %s, for the song %s' "${coverArtFile%.*}"  "$title")

# --- render template ------------------------------------------------------
export TITLE="$title"
export SLUG="$slug"
export DATE_TODAY="$date_today"
export COVER_ART_FILE="$coverArtFile"
export COVER_DESC="$cover_desc"
export SYNOPSIS="$synopsis"
export LYRICS_MD="$lyrics_md"

perl -0777 -pe '
  s/\{\{title\}\}/$ENV{TITLE}/g;
  s/\{\{slug\}\}/$ENV{SLUG}/g;
  s/\{\{date_today\}\}/$ENV{DATE_TODAY}/g;
  s/\{\{cover_art_file\}\}/$ENV{COVER_ART_FILE}/g;
  s/\{\{cover_image_desc\}\}/$ENV{COVER_DESC}/g;
  s/\{\{synopsis\}\}/$ENV{SYNOPSIS}/g;
  s/\{\{lyrics_md\}\}/$ENV{LYRICS_MD}/g;
' "$template_file" > "$release_dir/release.eno"

# --- move assets ----------------------------------------------------------

mv "${wav[0]}" "$release_dir/"

mv -- "$TPL/$coverArtFile" "$release_dir/$coverArtFile"

# marker to show build complete
touch "$release_dir/BUILT"

log "[sotd-build] Built $release_dir"

