#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/dox/st33v.com"
FORGE="$ROOT/forge"
IN="$FORGE/in"
OUT="$FORGE/out"
TPL="$FORGE/template"

die() { echo "[sotd-build] $*" >&2; exit 1; }

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

#---------------------------------------------------------------------------
title="$(cat "$TPL/title")"
date_today="$(date -I)"
slug_title="$(slugify "$title")"
slug="$date_today-$slug_title"

release_dir="$OUT/$slug"
mkdir -p "$release_dir"

cover_desc="Cover image for the song: $title"

has_lyrics=false
lyrics_md=""

if [[ -f "$TPL/lyrics" ]]; then
  has_lyrics=true
  lyrics_md="$(sed 's/$/  /' "$TPL/lyrics")"
fi

# synopsis: first ~3 lines, <256 chars, joined by " / "
synopsis=""
if $has_lyrics; then
  synopsis="$(head -n 3 "$TPL/lyrics" \
    | tr '\n' '/' \
    | sed 's|/| / |g' \
    | cut -c1-255)"
fi

# --- render template ------------------------------------------------------
export TITLE="$title"
export SLUG="$slug"
export DATE_TODAY="$date_today"
export COVER_DESC="$cover_desc"
export SYNOPSIS="$synopsis"
export LYRICS_MD="$lyrics_md"

release_eno="$release_dir/release.eno"

perl -0777 -pe '
  s/\{\{title\}\}/$ENV{TITLE}/g;
  s/\{\{slug\}\}/$ENV{SLUG}/g;
  s/\{\{date_today\}\}/$ENV{DATE_TODAY}/g;
  s/\{\{cover_image_desc\}\}/$ENV{COVER_DESC}/g;
  s/\{\{synopsis\}\}/$ENV{SYNOPSIS}/g;
  s/\{\{lyrics_md\}\}/$ENV{LYRICS_MD}/g;
' "$template_file" > "$release_eno"

# --- move assets ----------------------------------------------------------

mv "${wav[0]}" "$release_dir/"

if [[ -f "$TPL/cover.jpg" ]]; then
  cp "$TPL/cover.jpg" "$release_dir/cover.jpg"
fi

# marker to show build complete
touch "$release_dir/BUILT"

echo "[sotd-build] Built $release_dir"

