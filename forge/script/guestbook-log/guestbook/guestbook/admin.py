from __future__ import annotations

import argparse
import csv
import json
import sys

from .config import load_config
from .db import add_moderation_event, build_stats, connect, export_rows, get_entry, init_db, list_entries, search_entries, set_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="guestbook-admin")
    parser.add_argument("--config", default="config/config.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    list_pending = sub.add_parser("list-pending")
    list_pending.add_argument("--limit", type=int, default=50)

    recent = sub.add_parser("recent")
    recent.add_argument("--limit", type=int, default=20)

    search = sub.add_parser("search")
    search.add_argument("term")
    search.add_argument("--limit", type=int, default=20)

    for name in ("approve", "reject", "spam", "hide"):
        cmd = sub.add_parser(name)
        cmd.add_argument("entry_id", type=int)
        cmd.add_argument("--actor", default="admin")
        cmd.add_argument("--notes", default="")

    export = sub.add_parser("export")
    export.add_argument("--format", choices=["csv", "json"], default="csv")

    sub.add_parser("stats")
    sub.add_parser("init-db")
    return parser


def render_rows(rows) -> str:
    lines = []
    for row in rows:
        data = dict(row)
        lines.append(
            f"{data.get('id')}  {data.get('created_utc')}  {data.get('status', ''):<8}  {data.get('display_name', ''):<18}  {data.get('page_path', '')}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command == "init-db":
        init_db(config.database_path)
        print(f"initialized {config.database_path}")
        return 0

    with connect(config.database_path) as conn:
        if args.command == "list-pending":
            rows = list_entries(conn, status="pending", limit=args.limit)
            print(render_rows(rows))
            return 0
        if args.command == "recent":
            rows = list_entries(conn, status=None, limit=args.limit)
            print(render_rows(rows))
            return 0
        if args.command == "search":
            print(render_rows(search_entries(conn, args.term, limit=args.limit)))
            return 0
        if args.command in {"approve", "reject", "spam", "hide"}:
            entry = get_entry(conn, args.entry_id)
            if not entry:
                print(f"entry {args.entry_id} not found", file=sys.stderr)
                return 1
            status_map = {"approve": "approved", "reject": "rejected", "spam": "spam", "hide": "hidden"}
            set_status(conn, args.entry_id, status_map[args.command], args.actor, args.notes)
            print(f"{args.command}d entry {args.entry_id}")
            return 0
        if args.command == "stats":
            stats = build_stats(conn)
            print(json.dumps({"total": stats["total"], "pending": stats["pending"], "approved": stats["approved"], "spam": stats["spam"]}, indent=2))
            for row in stats["pages"]:
                print(f"{row['total']:>4}  {row['page_path']}")
            return 0
        if args.command == "export":
            rows = [dict(row) for row in export_rows(conn)]
            if args.format == "json":
                print(json.dumps(rows, indent=2, default=str))
                return 0
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

