# Reordering Spec for `playlist.m3u`

## 0. Section Zero: Document Information

| Field | Value |
|---|---|
| Document Title | Reordering Spec for `playlist.m3u` |
| Intended Implementer | Codex |
| Intended User | Stephen |
| Status | Draft |
| Primary Goal | Rewrite an existing `.m3u` playlist into newest-first chronological order |
| Assumption | The current playlist file will be placed in the working directory and used as the input template |
| Preferred Output Style | Minimal, robust, CLI-friendly, Arch Linux compatible |
| Suggested Languages | Shell wrapper plus Python for parsing/sorting |
| Out of Scope | Changing Faircamp internals; changing nginx; editing audio metadata at source |

---

## TL;DR

Build a small local tool that reads an existing `playlist.m3u` file from the current working directory, parses it as an extended M3U playlist, extracts the track date from each track URL, sorts entries newest-first, removes blank-line noise, and writes a clean reordered playlist. The tool should preserve playlist-level header metadata where sensible, preserve each track’s `#EXTINF` plus URL pairing, and fail clearly if an entry cannot be parsed. Provide a shell entrypoint, a Python implementation, a README, and a few test fixtures.

---

# 1. Purpose

### 1.1
The purpose of this tool is to post-process an already generated playlist file such as `playlist.m3u` and produce a deterministic, clean, newest-first version of that playlist.

### 1.2
The tool exists because the upstream generator currently emits the playlist in a non-preferred order.

### 1.3
The desired order is chronological by date extracted from each track URL, with the newest dated entry first.

### 1.4
The tool should be normally executed by a call from ../stagePublisher.sh . It may also be run standalone and should not require modification of the upstream site generator.

---

# 2. Primary Use Case

### 2.1
The user generates or updates a site playlist.

### 2.2
The user copies or places the current playlist file into a working directory.

### 2.3
The tool is run locally against that playlist.

### 2.4
The tool outputs a cleaned and reordered playlist file suitable for deployment.

---

# 3. Scope

## 3.1 In Scope

### 3.1.1
Parsing an existing extended M3U playlist.

### 3.1.2
Preserving top-level playlist metadata lines such as:

- `#EXTM3U`
- `#EXTENC:...`
- `#PLAYLIST:...`
- `#EXTIMG:...`
- `#EXTALB:...`

### 3.1.3
Parsing each playlist item as a logical record consisting of:

- one `#EXTINF:...` line
- one following media URL line

### 3.1.4
Ignoring blank lines between records.

### 3.1.5
Extracting a date from the media URL using a robust date pattern.

### 3.1.6
Sorting records newest-first by extracted date.

### 3.1.7
Writing a valid, clean `.m3u` file with no extraneous blank lines.

### 3.1.8
Providing clear errors and a non-zero exit code if parsing fails.

---

## 3.2 Out of Scope

### 3.2.1
Editing or regenerating Faircamp source data.

### 3.2.2
Changing per-track metadata inside audio files.

### 3.2.3
Fixing browser association behaviour.

### 3.2.4
Renaming release directories or altering website URLs.

### 3.2.5
Building a general-purpose playlist editor UI.

---

# 4. Input Assumptions

### 4.1
The input file is an extended M3U playlist, normally named `playlist.m3u`, present in the sotd/ directory.

### 4.2
The file may contain blank lines between logical entries.

### 4.3
The file may contain playlist-level header metadata before the track entries.

### 4.4
Each logical track entry is expected to contain exactly one `#EXTINF:` line followed by exactly one URL/media path line.

### 4.5
The media URL is expected to contain a date in ISO form somewhere in the path, matching:

`YYYY-MM-DD`

### 4.6
The date may occur inside slugs of either of these kinds:

- `2026-03-30-enthalpiclore`
- `sotd-2026-01-30`

### 4.7
The script must not assume a fixed slug prefix; it must search for the date pattern anywhere in the URL path.

---

# 5. Output Requirements

### 5.1
The output must be a valid extended M3U file.

### 5.2
The output must preserve the top-level header block in original order.

### 5.3
The output must preserve each track’s original `#EXTINF:` line and original media URL line verbatim, except for surrounding whitespace cleanup.

### 5.4
The output must contain no blank lines between track records unless explicitly configured otherwise.

### 5.5
The output ordering must be newest-first by extracted date.

### 5.6
If two entries share the same date, the tool should preserve their original relative order as a stable secondary ordering rule.

### 5.7
The default output filename should be:

`playlist.sorted.m3u`

### 5.8
An optional in-place mode may overwrite the original file, but only when explicitly requested by a flag.

---

# 6. Sorting Rules

### 6.1
Primary sort key: extracted date from media URL.

### 6.2
Sort direction: descending, newest first.

### 6.3
Secondary sort key: original appearance order in the input file, to ensure stable behaviour.

### 6.4
The script must not sort by title, duration, slug text, or filename except as a consequence of stable ordering.

---

# 7. Parsing Rules

## 7.1 Header Parsing

### 7.1.1
All leading lines beginning with `#` before the first `#EXTINF:` should be treated as playlist-level header metadata and preserved.

### 7.1.2
Blank lines in the header block may be ignored or normalized away.

---

## 7.2 Entry Parsing

### 7.2.1
A track entry begins at `#EXTINF:`.

### 7.2.2
The first subsequent non-blank, non-comment line after `#EXTINF:` is the media URL/path for that entry.

### 7.2.3
Blank lines between `#EXTINF:` and URL should be tolerated but not preserved.

### 7.2.4
Unexpected comment lines between `#EXTINF:` and URL should trigger either:
- a hard error, or
- a warning plus skip,
depending on the chosen strictness mode.

Default should be hard error.

---

## 7.3 Date Extraction

### 7.3.1
The implementation must search the media URL/path for the first occurrence of the regex:

`\d{4}-\d{2}-\d{2}`

### 7.3.2
That match should be interpreted as the entry date.

### 7.3.3
The date should be parsed into a real date object for comparison, not compared as raw text only.

### 7.3.4
If no valid date can be found, the tool must fail with a clear error message that includes the offending URL and entry number.

---

# 8. CLI Requirements

## 8.1 Default Invocation

### 8.1.1
Default usage should be as simple as:

```bash
./reorder_playlist.m3u.sh
