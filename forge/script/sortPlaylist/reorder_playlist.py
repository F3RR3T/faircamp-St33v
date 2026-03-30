#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


class PlaylistError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    metadata: tuple[str, ...]
    extinf: str
    url: str
    date: dt.date
    index: int


def extract_date(url: str, entry_number: int) -> dt.date:
    match = DATE_RE.search(url)
    if not match:
        raise PlaylistError(
            f"entry {entry_number}: no YYYY-MM-DD date found in URL: {url}"
        )

    date_text = match.group(0)
    try:
        return dt.date.fromisoformat(date_text)
    except ValueError as exc:
        raise PlaylistError(
            f"entry {entry_number}: invalid date {date_text!r} in URL: {url}"
        ) from exc


def parse_playlist(text: str) -> tuple[list[str], list[Entry]]:
    lines = text.splitlines()
    header: list[str] = []
    entries: list[Entry] = []
    idx = 0
    pending_metadata: list[str] = []
    saw_entries = False
    seen_header_image = False

    while idx < len(lines):
        raw = lines[idx].strip()

        if not raw:
            idx += 1
            continue

        if raw.startswith("#") and not raw.startswith("#EXTINF:"):
            if saw_entries:
                pending_metadata.append(raw)
            else:
                if raw.startswith("#EXTALB:"):
                    pending_metadata.append(raw)
                elif raw.startswith("#EXTIMG:"):
                    if seen_header_image:
                        pending_metadata.append(raw)
                    else:
                        header.append(raw)
                        seen_header_image = True
                else:
                    if pending_metadata:
                        pending_metadata.append(raw)
                    else:
                        header.append(raw)
            idx += 1
            continue

        if not raw.startswith("#EXTINF:"):
            if saw_entries:
                raise PlaylistError(f"expected #EXTINF line for entry {len(entries) + 1}, got: {raw}")
            raise PlaylistError(f"unexpected non-comment line in header: {raw}")

        saw_entries = True
        extinf = raw
        idx += 1
        url = None

        while idx < len(lines):
            candidate = lines[idx].strip()
            idx += 1

            if not candidate:
                continue
            if candidate.startswith("#"):
                raise PlaylistError(
                    f"entry {len(entries) + 1}: unexpected comment before URL: {candidate}"
                )
            url = candidate
            break

        if url is None:
            raise PlaylistError(f"entry {len(entries) + 1}: missing URL after {extinf}")

        entries.append(
            Entry(
                metadata=tuple(pending_metadata),
                extinf=extinf,
                url=url,
                date=extract_date(url, len(entries) + 1),
                index=len(entries),
            )
        )
        pending_metadata.clear()

    if pending_metadata:
        raise PlaylistError(
            f"dangling metadata without trailing #EXTINF: {pending_metadata[-1]}"
        )

    return header, entries


def render_playlist(header: list[str], entries: list[Entry]) -> str:
    output: list[str] = []
    output.extend(header)
    for entry in entries:
        output.extend(entry.metadata)
        output.append(entry.extinf)
        output.append(entry.url)
    return "\n".join(output) + "\n"


def sort_entries(entries: list[Entry]) -> list[Entry]:
    return sorted(entries, key=lambda entry: (entry.date, -entry.index), reverse=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sort an extended M3U playlist newest-first by date found in each entry URL."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="playlist.m3u",
        help="Input playlist path (default: playlist.m3u)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="playlist.sorted.m3u",
        help="Output path when not using --in-place (default: playlist.sorted.m3u)",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input playlist instead of writing a separate output file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = input_path if args.in_place else Path(args.output)

    try:
        text = input_path.read_text(encoding="utf-8")
        header, entries = parse_playlist(text)
        sorted_entries = sort_entries(entries)
        output_path.write_text(
            render_playlist(header, sorted_entries),
            encoding="utf-8",
        )
    except FileNotFoundError:
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 1
    except PlaylistError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
