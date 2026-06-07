---
title: "Sitemap dedup — content pages only"
date-created: "2026-06-07"
version: "0.1"
type: "spec"
author:
  - "st33v"
  - "claude-opus-4-8"
model:
  - "claude-opus-4-8"
tldr: "Shrink sitemap.xml and kill the release/track double-jump by emitting one canonical content URL per song. Drop redundant single-track release track-pages; keep multi-track album track-pages (they carry per-track lyrics); optionally drop media assets."
status: "draft"
spec-kind: "tooling"
target-repo: "st33v.com"
target-machine: "cr4y"
dependencies: []
design-chat: ""
phase: "1"
phases-planned: 1
implementing-agent: "claude-code"
provenance-urls:
  - "https://st33v.com/sitemap.xml"
---

# Sitemap dedup — content pages only

Modify the existing sitemap-generation script so the emitted `sitemap.xml`
lists exactly one canonical, content-bearing URL per song, and no media.
Goal: smaller file, no duplicate page that looks the same but lacks lyrics.

> **Confirm before starting:** `target-repo` / `target-machine` above are a
> best guess — point Claude Code at the actual script that emits `sitemap.xml`
> and read its current logic first; implement the rules below in its own idiom.

## Background — the duplication

Faircamp emits, per release:

- a **release page** `/<release>/index.html`
- a **track page** `/<release>/<n>/index.html` for each track `<n>`
- media assets under `/<release>/<n>/{mp3-v5,opus-96}/…` and `downloads/…`

The lyrics location differs by release shape:

- **Single-track release** (every SOTD entry): lyrics render on the *release
  page*. The lone track page `/<release>/1/` is a duplicate → **redundant**
  (this is the "double jump").
- **Multi-track release** (the albums: `nextex`, `colloquium`, `endofmusic`,
  `message`, `bgmusic`): each *track page* carries that track's own lyrics; the
  release page carries only liner notes. Track pages are **not** redundant.

A naïve "strip any `/<digits>/` URL" rule is therefore wrong — it would delete
every album track's lyric page. The real distinction is track count.

## Rules

- **R1 — Release pages:** always emit `/<release>/index.html`.
- **R2 — Track pages:** emit `/<release>/<n>/index.html` **only if the release
  has ≥ 2 tracks**. Drop the track page of every single-track release. This
  removes the double-jump.
- **R3 — Media + downloads (size win, default ON, reversible):** drop all
  `*.mp3`, `*.opus`, and `**/downloads/**` URLs. A page sitemap indexes HTML,
  not assets. Gate behind a flag (e.g. `--include-media`, default off) so it
  can be restored without code edits.
- **R4 — Navigational indexes:** keep section/listing and artist pages as-is
  (`/`, `/sotd/index.html`, `/drmorbius/`, `/eli/`, `/image-descriptions/`).
  They are not duplicates.

### Determining track count

Count the numbered track subdirectories matching `^\d+$` directly under each
release directory (or reuse the release/track model the script already holds).
`1` → single-track (apply R2 drop); `≥ 2` → multi-track (keep track pages).

## Done when

- No `/<release>/1/…` page entries remain for single-track releases.
- All multi-track album track pages (`/nextex/4/…` etc.) are still present.
- With R3 on: no `.mp3`, `.opus`, or `downloads` entries remain.
- `<lastmod>` is preserved verbatim for every URL that is kept.
- Output still validates against the sitemaps.org 0.9 schema.
- Script logs entry count before/after as a sanity check.

## Out of scope

- No change to Faircamp output or page content; sitemap emission only.
- No new dependencies; stay on whatever the script already uses (stdlib pref.).
- A separate media/video sitemap, if ever wanted, is a future phase.
