# SOTD Audio Mastering Spec (Codex Work Order)

## Summary
Create a new executable that is invoked by `build-sotd.sh` to process an imported Suno `.wav` for Song of the Day (SOTD). The executable will:

1) read metadata (title + SOTD date),
2) embed metadata into the audio,
3) apply **light mastering** and **loudness normalization to -12 LUFS (integrated)**,
4) write the mastered result to **FLAC** (lossless + slight compression),
5) archive the original WAV into `rawAudio/`.

Faircamp will ingest the FLAC and produce MP3s for upload. No transcoding logic is required here beyond producing the FLAC.

---

## Directory layout and invocation context

### Existing script location
- Existing scripts live in: `forge/scripts/`
- Codex working directory (pwd) when implementing is: `forge/scripts/`

### Raw archival directory
- Original WAVs are moved to: `forge/rawAudio/` after processing.
  - Location should be treated as relative to the repo root unless already defined elsewhere in the SOTD scripts. Prefer using the same conventions already present in `build-sotd.sh` (Codex should inspect and follow existing path patterns).

---

## New executable

### Name + location
- Create a new executable file in `forge/scripts/`
- Must be directly runnable by `build-sotd.sh` (no interactive prompts)

### How it is called
- `build-sotd.sh` will call this executable once per SOTD import.
- Codex should update `build-sotd.sh` to call the executable at the appropriate point, but must keep the remainder of the pipeline behavior unchanged.

### Inputs
The executable must accept, at minimum:
- the path to the imported Suno WAV file (input WAV)
- the current date in ISO format `YYYY-MM-DD`.

Codex should determine the cleanest interface based on how `build-sotd.sh` currently handles:
- the “current SOTD date”
- the imported audio filename conventions
- the build tree paths

### Output
- A mastered **FLAC** file written to the expected location for Faircamp ingestion (Codex to align with existing SOTD build layout).
- The input WAV must be moved to `rawAudio/` after successful processing.

---

## Metadata requirements

### Title
- Read title from: `template/title`
  - This file is the source of truth.
  - Treat the file contents as UTF-8 text.
  - Preserve punctuation and case.
  - Trim trailing newlines.

### Album
'Song of the Day'

### Artist
'St33v™'

### Comment tag
Write a comment field that includes both:
- `SOTD <date>`
- `Licence: CC BY-NC-SA 4.0`

Example (exact formatting requirement):
- `SOTD 2026-02-23 | Licence: CC BY-NC-SA 4.0`

Notes:
- Use the exact spelling `Licence:` (not `License:`).
- Date must be ISO `YYYY-MM-DD`.

---

## Audio mastering requirements

### Target loudness
- **-12 LUFS integrated**

### Peak safety
- Must control peaks to prevent clipping.
- Prefer a conservative true-peak ceiling suitable for web playback (Codex to choose a sensible value; must be documented in comments/log output).

### “Light mastering” definition
The processing chain should be conservative and repeatable. Goals:
- High pass filter at about 50 Hz to clarify bass.
- modest dynamic control (gentle compression and/or limiting),
- no audible pumping,
- avoid tonal rebalancing unless minimal and necessary,
- consistent perceived loudness across SOTDs.

Codex should implement a small, stable chain that works well across varied Suno outputs.

### Idempotence / double-processing avoidance
- The pipeline must not repeatedly master the same file if the build step is rerun.
- Codex must implement a guard such as:
  - output existence check,
  - naming convention,
  - or a small marker file/manifest.
- Must not overwrite mastered output without an explicit reason.

---

## Logging + verification
The executable must write clear logs to stdout/stderr suitable for inclusion in existing build logs, including:
- input file path
- output file path
- title used
- comment string used
- measured loudness (at least post-process; ideally pre and post)
- peak/true-peak value post-process (or an equivalent safety metric depending on tooling)

On failure:
- Exit non-zero.
- Do not delete the input WAV.
- Do not emit a partial/invalid FLAC in the ingestion location (clean up temp artifacts).

---

## Tooling constraints (Arch Linux)
- Must use CLI tooling available on Arch (pacman/AUR acceptable, ask user to install any packages not already present).
- No GUI tools, no interactive prompts.
- Keep dependencies minimal and documented (Codex should add notes in a comment header).

---

## Acceptance criteria (definition of done)
1) Running `build-sotd.sh` on a new WAV produces a FLAC that Faircamp can ingest.
2) The resulting FLAC contains:
   - title from `template/title`
   - comment containing `SOTD <date>` and `Licence: CC BY-NC-SA 4.0`
3) The resulting FLAC measures **-12 LUFS integrated** within a small tolerance suitable for the chosen toolchain.
4) Peaks are controlled (no clipping).
5) Original WAV is moved to `rawAudio/` only after successful completion.
6) Re-running the pipeline does not “double master” or drift the audio output.

---
