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

date_today="$(date -I)"
slug="sotd-$date_today"

release_dir="$OUT/$slug"
mkdir -p "$release_dir"

title="$(cat "$TPL/title")"
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

release_eno="$release_dir/release.eno"

sed \
  -e "s|{{title}}|$title|g" \
  -e "s|{{slug}}|$slug|g" \
  -e "s|{{date_today}}|$date_today|g" \
  -e "s|{{cover_image_desc}}|$cover_desc|g" \
  -e "s|{{synopsis}}|$synopsis|g" \
  -e "s|{{lyrics_md}}|$lyrics_md|g" \
  "$template_file" > "$release_eno"

# --- move assets ----------------------------------------------------------

mv "${wav[0]}" "$release_dir/song.wav"

if [[ -f "$TPL/cover.jpg" ]]; then
  cp "$TPL/cover.jpg" "$release_dir/cover.jpg"
fi

# marker to show build complete
touch "$release_dir/BUILT"

echo "[sotd-build] Built $release_dir"

