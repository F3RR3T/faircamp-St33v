#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import unquote, urlparse


LOG_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<request>[^"]*)" (?P<status>\d{3}) (?P<bytes>\S+) '
    r'"(?P<referer>[^"]*)" "(?P<ua>[^"]*)"'
)

AUDIO_EXTS = {".mp3", ".ogg", ".opus", ".m4a", ".flac", ".wav", ".aac"}
ASSET_EXTS = {
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".webp", ".avif", ".mp4", ".webm", ".pdf", ".zip", ".tar", ".gz",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


def parse_args():
    p = argparse.ArgumentParser(description="Generate daily nginx access log digest.")
    p.add_argument("--log", action="append", default=None, help="Path to access log (can be repeated)")
    p.add_argument("--bots", default=None, help="Path to bots.txt")
    p.add_argument("--outdir", default=None, help="Output directory for markdown reports")
    p.add_argument("--date", default="yesterday", help="Report date in UTC (YYYY-MM-DD) or 'yesterday'")
    return p.parse_args()


def load_bots(path):
    patterns = []
    if not path or not os.path.exists(path):
        return patterns
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                patterns.append(re.compile(line, re.IGNORECASE))
            except re.error:
                continue
    return patterns


def is_bot(ua, patterns):
    if not ua:
        return False
    for pat in patterns:
        if pat.search(ua):
            return True
    return False


def request_parts(request):
    if not request or request == "-":
        return None, None, None
    parts = request.split()
    if len(parts) < 2:
        return None, None, None
    method = parts[0]
    path = parts[1]
    proto = parts[2] if len(parts) > 2 else None
    return method, path, proto


def path_no_query(path):
    try:
        return urlparse(path).path or "/"
    except Exception:
        return path


def canonical_track_rollup(path):
    parts = [p for p in path_no_query(path).split("/") if p]
    if not parts:
        return None

    if parts[0] == "sotd":
        # /sotd/<album_slug>/<track>/<anything...>/<song_file_name>
        if len(parts) < 4:
            return None
        album = "sotd"
        track = parts[2]
        song_file_name = parts[-1]
    else:
        # /<album_slug>/<track>/<anything...>/<song_file_name>
        if len(parts) < 3:
            return None
        album = parts[0]
        track = parts[1]
        song_file_name = parts[-1]

    ext = os.path.splitext(song_file_name.lower())[1]
    if ext not in AUDIO_EXTS:
        return None
    if not track:
        return None

    track_name = unquote(os.path.splitext(song_file_name)[0])
    return album, track_name


def _selftest_canonical_track_rollup():
    # Tiny examples:
    # 1) format/hash + codec/ext variants collapse to one key
    # 2) non-audio requests are ignored
    a = "/sotd/2026-02-16-goldenbraidneuralfire/1/mp3-v5/XYZ/01%20goldenBraid.mp3"
    b = "/sotd/2026-02-16-goldenbraidneuralfire/1/opus-96/ABC/01%20goldenBraid.opus"
    expected = ("sotd", "01 goldenBraid")
    assert canonical_track_rollup(a) == expected
    assert canonical_track_rollup(b) == expected
    assert canonical_track_rollup("/my-album/1/cover.jpg") is None


def parse_time(ts):
    # Example: 10/Oct/2000:13:55:36 -0700
    return dt.datetime.strptime(ts, "%d/%b/%Y:%H:%M:%S %z")


def date_range_utc(date_str):
    if date_str == "yesterday":
        now = dt.datetime.now(dt.timezone.utc)
        day = (now - dt.timedelta(days=1)).date()
    else:
        day = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    start = dt.datetime.combine(day, dt.time(0, 0, 0), dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    return day, start, end


def iter_logs(paths):
    for path in paths:
        if not path or not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line.rstrip("\n")


def main():
    args = parse_args()
    logs = args.log or ["/var/log/nginx/access.log", "/var/log/nginx/access.log.1"]
    bots_path = args.bots or "/opt/nginx-digest/bots.txt"
    outdir = args.outdir or "/home/st33v/nginx-digest/daily"

    day, start_utc, end_utc = date_range_utc(args.date)
    bot_patterns = load_bots(bots_path)

    totals_requests = 0
    visitors = set()
    page_views = Counter()
    plays = Counter()
    play_bytes = defaultdict(int)
    track_counts = Counter()
    track_bytes = defaultdict(int)
    referrers = Counter()
    bot_uas = Counter()
    not_found = Counter()

    for line in iter_logs(logs):
        m = LOG_RE.match(line)
        if not m:
            continue

        try:
            t_local = parse_time(m.group("time"))
        except Exception:
            continue
        t_utc = t_local.astimezone(dt.timezone.utc)
        if not (start_utc <= t_utc < end_utc):
            continue

        ip = m.group("ip")
        ua = m.group("ua")
        status = int(m.group("status"))
        bytes_sent = m.group("bytes")
        bytes_sent = int(bytes_sent) if bytes_sent.isdigit() else 0
        referer = m.group("referer")

        if is_bot(ua, bot_patterns):
            bot_uas[ua] += 1
            continue

        totals_requests += 1

        method, path, _ = request_parts(m.group("request"))
        if not path:
            continue
        path = path_no_query(path)

        visitors.add((ip, ua))

        ext = os.path.splitext(path.lower())[1]

        if status == 404:
            not_found[path] += 1

        if method == "GET" and status == 200 and ext and ext in ASSET_EXTS:
            continue
        if method == "GET" and status == 200 and path == "/favicon.ico":
            continue

        if method == "GET" and ext in AUDIO_EXTS and status in (200, 206):
            key = (ip, ua, path)
            plays[key] += 1
            if bytes_sent > play_bytes[key]:
                play_bytes[key] = bytes_sent
            track_key = canonical_track_rollup(path)
            if track_key:
                track_counts[track_key] += 1
                track_bytes[track_key] += bytes_sent
        elif method == "GET" and status == 200:
            page_views[path] += 1

        if referer and referer != "-":
            referrers[referer] += 1

    unique_visitors = len(visitors)
    total_page_views = sum(page_views.values())
    total_plays = len(plays)

    report_lines = []
    report_lines.append(f"# Nginx Digest {day.isoformat()} (UTC)")
    report_lines.append("")
    report_lines.append("## Totals")
    report_lines.append(f"- Requests: {totals_requests}")
    report_lines.append(f"- Unique visitors: {unique_visitors}")
    report_lines.append(f"- Page views: {total_page_views}")
    report_lines.append(f"- Plays: {total_plays}")
    report_lines.append("")

    report_lines.append("## Top 10 Tracks (by plays)")
    if track_counts:
        top_tracks = sorted(
            track_counts.items(),
            key=lambda kv: (-kv[1], -track_bytes.get(kv[0], 0), kv[0]),
        )[:10]
        for idx, (track_key, cnt) in enumerate(top_tracks, start=1):
            b = track_bytes.get(track_key, 0)
            kb = b / 1024.0
            album, track_name = track_key
            report_lines.append(f"{idx}. {album} / {track_name} — {cnt} plays, {kb:.1f} kB")
    else:
        report_lines.append("- None")
    report_lines.append("")

    report_lines.append("## Top 10 Pages (by hits)")
    if page_views:
        for path, cnt in page_views.most_common(10):
            report_lines.append(f"- {path} — {cnt}")
    else:
        report_lines.append("- None")
    report_lines.append("")

    report_lines.append("## Top Referrers")
    if referrers:
        for ref, cnt in referrers.most_common(10):
            report_lines.append(f"- {ref} — {cnt}")
    else:
        report_lines.append("- None")
    report_lines.append("")

    report_lines.append("## Notable Bots/Scanners")
    if bot_uas:
        for ua, cnt in bot_uas.most_common(10):
            report_lines.append(f"- {ua} — {cnt}")
    else:
        report_lines.append("- None")
    report_lines.append("")

    report_lines.append("## Top 10 404 Paths")
    if not_found:
        for path, cnt in not_found.most_common(10):
            report_lines.append(f"- {path} — {cnt}")
    else:
        report_lines.append("- None")
    report_lines.append("")

    os.makedirs(outdir, exist_ok=True)
    out_path = os.path.join(outdir, f"{day.isoformat()}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines).rstrip() + "\n")

    print(out_path)


if __name__ == "__main__":
    if os.environ.get("NGINX_DIGEST_SELFTEST") == "1":
        _selftest_canonical_track_rollup()
    main()
