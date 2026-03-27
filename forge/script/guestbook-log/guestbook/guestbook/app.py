from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from html import escape
import logging
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from .config import Config, load_config, load_wordlists
from .db import (
    connect,
    count_public_entries,
    fetch_public_entries,
    init_db,
    last_submission_time,
    rate_limit_snapshot,
    record_entry,
    utc_now,
    utc_now_text,
)
from .filters import analyze_text, ip_hash, normalize_page_path
from .markdown_utils import render_comment


class GuestbookApp:
    def __init__(self, config: Config):
        self.config = config
        self.wordlists = load_wordlists(config)
        self.logger = logging.getLogger("guestbook")

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        try:
            if path == f"{self.config.base_path}/health":
                return self.respond_text(start_response, "200 OK", "ok\n")
            if path == f"{self.config.base_path}/guidelines":
                return self.respond_html(start_response, self.guidelines_page())
            if path == f"{self.config.base_path}/all":
                return self.respond_html(start_response, self.all_comments_page())
            if path == f"{self.config.base_path}/page":
                params = parse_qs(environ.get("QUERY_STRING", ""))
                page_path = normalize_page_path(params.get("path", ["/"])[0])
                return self.respond_html(start_response, self.page_comments_page(page_path))
            if path == f"{self.config.base_path}/count":
                params = parse_qs(environ.get("QUERY_STRING", ""))
                page_path = normalize_page_path(params.get("path", ["/"])[0])
                with connect(self.config.database_path) as conn:
                    count = count_public_entries(conn, page_path)
                return self.respond_json(start_response, {"page_path": page_path, "approved_count": count})
            if path == f"{self.config.base_path}/form":
                params = parse_qs(environ.get("QUERY_STRING", ""))
                page_path = normalize_page_path(params.get("path", ["/"])[0])
                page_title = params.get("title", [""])[0]
                return self.respond_html(start_response, self.form_page(page_path, page_title))
            if path == f"{self.config.base_path}/submit" and method == "POST":
                return self.handle_submit(environ, start_response)
            return self.respond_html(start_response, self.not_found_page(), status="404 Not Found")
        except Exception:
            self.logger.exception("request failed", extra={"path": path, "method": method})
            return self.respond_html(start_response, self.error_page(), status="500 Internal Server Error")

    def handle_submit(self, environ, start_response):
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            length = 0
        body = environ["wsgi.input"].read(length).decode("utf-8", errors="replace")
        form = parse_qs(body)

        name = form.get("display_name", [""])[0].strip()
        comment = form.get("comment", [""])[0].strip()
        honeypot = form.get("homepage", [""])[0]
        page_path = normalize_page_path(form.get("page_path", ["/"])[0])
        page_url = form.get("page_url", [""])[0].strip()
        page_title = form.get("page_title", [""])[0].strip()
        rendered_at = form.get("rendered_at", ["0"])[0]
        acknowledgement = form.get("acknowledgement", [""])[0]
        submission_token = form.get("submission_token", [""])[0].strip()

        errors = self.validate_submission(name, comment, acknowledgement)
        if errors:
            return self.respond_html(
                start_response,
                self.form_page(page_path, page_title, errors=errors, values=form, status_note="Please fix the highlighted issues."),
                status="400 Bad Request",
            )

        now = utc_now()
        try:
            rendered_seconds = int(rendered_at)
        except ValueError:
            rendered_seconds = int(now.timestamp())
        elapsed_seconds = max(0, int(now.timestamp()) - rendered_seconds)

        ip_address = self.client_ip(environ)
        with connect(self.config.database_path) as conn:
            rate_state = rate_limit_snapshot(conn, ip_address)
            last_time = last_submission_time(conn, ip_address)
            if last_time and (now - last_time).total_seconds() < self.config.cooldown_seconds:
                return self.respond_html(start_response, self.message_page("Slow down", "Please wait a little before posting again."), status="429 Too Many Requests")
            if rate_state["hour"] >= self.config.max_per_hour or rate_state["day"] >= self.config.max_per_day:
                return self.respond_html(start_response, self.message_page("Rate limited", "Too many recent submissions from this address. Try again later."), status="429 Too Many Requests")

            filter_result = analyze_text(name, comment, page_path, honeypot, elapsed_seconds, self.config, self.wordlists)
            if filter_result.status == "rejected":
                self.logger.info("submission rejected", extra={"ip": ip_address, "page_path": page_path, "flags": filter_result.flags})
                return self.respond_html(start_response, self.message_page("Could not accept that note", "Your note could not be accepted in its current form."), status="400 Bad Request")

            entry = {
                "created_utc": utc_now_text(),
                "updated_utc": None,
                "status": filter_result.status,
                "display_name": name,
                "comment_raw": comment,
                "comment_rendered": render_comment(comment),
                "page_url": page_url[:1024],
                "page_path": page_path,
                "page_title": page_title[:200],
                "referrer": environ.get("HTTP_REFERER", "")[:1024],
                "ip_address": ip_address,
                "ip_hash": ip_hash(ip_address, self.config.secret_key),
                "user_agent": environ.get("HTTP_USER_AGENT", "")[:512],
                "accept_language": environ.get("HTTP_ACCEPT_LANGUAGE", "")[:255],
                "submission_token": submission_token[:120],
                "honeypot_value": honeypot[:255],
                "filter_score": filter_result.score,
                "filter_flags": filter_result.flags,
                "source_kind": "web_form",
                "notes_internal": filter_result.notes,
                "is_deleted": 0,
            }
            entry_id = record_entry(conn, entry)
            self.logger.info(
                "submission stored",
                extra={"entry_id": entry_id, "status": filter_result.status, "ip": ip_address, "page_path": page_path, "flags": filter_result.flags},
            )

        if filter_result.status == "approved":
            title = "Note posted"
            detail = "Your note is now visible on this page."
        elif filter_result.status == "pending":
            title = "Note received"
            detail = "Your note is queued for review."
        else:
            title = "Note rejected"
            detail = "Your note was blocked."
        return self.respond_html(start_response, self.message_page(title, detail, page_path=page_path))

    def validate_submission(self, name: str, comment: str, acknowledgement: str) -> list[str]:
        errors = []
        if not name or not name.strip():
            errors.append("Name is required.")
        if len(name) > self.config.max_name_length:
            errors.append(f"Name must be at most {self.config.max_name_length} characters.")
        if not comment or len(comment.strip()) < self.config.min_comment_length:
            errors.append(f"Comment must be at least {self.config.min_comment_length} characters.")
        if len(comment) > self.config.max_comment_length:
            errors.append(f"Comment must be at most {self.config.max_comment_length} characters.")
        if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in f"{name}{comment}"):
            errors.append("Control characters are not allowed.")
        if self.config.require_acknowledgement and acknowledgement != "yes":
            errors.append("Please confirm the good-faith note.")
        return errors

    def client_ip(self, environ) -> str:
        forwarded = environ.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
        return (environ.get("REMOTE_ADDR") or "0.0.0.0")[:64]

    def respond_html(self, start_response, content: str, status: str = "200 OK"):
        data = content.encode("utf-8")
        start_response(status, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))])
        return [data]

    def respond_text(self, start_response, status: str, content: str):
        data = content.encode("utf-8")
        start_response(status, [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(data)))])
        return [data]

    def respond_json(self, start_response, payload: dict, status: str = "200 OK"):
        import json

        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data)))])
        return [data]

    def layout(self, title: str, body: str) -> str:
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} | {escape(self.config.site_name)}</title>
  <style>
    :root {{
      --bg: #f5f0e6;
      --ink: #1d1a17;
      --accent: #8e3b2e;
      --panel: #fffaf1;
      --line: #d7c7af;
      --muted: #6d6359;
    }}
    body {{ margin: 0; font-family: Georgia, "Times New Roman", serif; background: linear-gradient(180deg, #efe6d4 0%, #f8f5ef 100%); color: var(--ink); }}
    main {{ max-width: 800px; margin: 0 auto; padding: 2rem 1rem 4rem; }}
    h1, h2 {{ font-weight: 600; letter-spacing: 0.01em; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.06); margin-bottom: 1rem; }}
    .meta, .hint {{ color: var(--muted); font-size: 0.95rem; }}
    .entry {{ border-top: 1px solid var(--line); padding-top: 0.8rem; margin-top: 0.8rem; }}
    label {{ display: block; font-weight: 600; margin-bottom: 0.3rem; }}
    input[type=text], textarea {{ width: 100%; box-sizing: border-box; border: 1px solid var(--line); border-radius: 10px; padding: 0.8rem; font: inherit; background: #fff; }}
    textarea {{ min-height: 12rem; resize: vertical; }}
    button {{ border: 0; border-radius: 999px; padding: 0.8rem 1.2rem; background: var(--accent); color: #fff8f2; font: inherit; cursor: pointer; }}
    a {{ color: var(--accent); }}
    ul.errors {{ color: #8b0000; }}
    .actions {{ display: flex; gap: 0.8rem; flex-wrap: wrap; margin-top: 1rem; }}
    .guidelines {{ font-style: italic; }}
    .sr-only {{ position: absolute; left: -10000px; }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>"""

    def form_page(self, page_path: str, page_title: str = "", errors: list[str] | None = None, values: dict | None = None, status_note: str = "") -> str:
        values = values or {}
        name = escape((values.get("display_name", [""])[0] if isinstance(values.get("display_name"), list) else ""))
        comment = escape((values.get("comment", [""])[0] if isinstance(values.get("comment"), list) else ""))
        now_seconds = int(datetime.now(timezone.utc).timestamp())
        error_html = ""
        if errors:
            error_html = "<ul class='errors'>" + "".join(f"<li>{escape(msg)}</li>" for msg in errors) + "</ul>"
        ack_html = ""
        if self.config.require_acknowledgement:
            ack_html = """
  <label><input type="checkbox" name="acknowledgement" value="yes"> I’m posting in good faith.</label>
"""
        body = f"""
<section class="card">
  <h1>Leave a note for this page</h1>
  <p class="meta">Page: <code>{escape(page_path)}</code></p>
  <p class="guidelines">This guestbook is for sincere remarks, responses, and sightings from fellow travellers. Spam, scams, and hostile nonsense are unwelcome. Links may be filtered and notes may be moderated.</p>
  {f'<p class="hint">{escape(status_note)}</p>' if status_note else ''}
  {error_html}
  <form method="post" action="{escape(self.config.base_path)}/submit">
    <label for="display_name">Name</label>
    <input id="display_name" name="display_name" type="text" maxlength="{self.config.max_name_length}" value="{name}" required>
    <label for="comment">Comment</label>
    <textarea id="comment" name="comment" maxlength="{self.config.max_comment_length}" required>{comment}</textarea>
    <p class="hint">Markdown is allowed. Raw HTML is not.</p>
    {ack_html}
    <input type="hidden" name="page_path" value="{escape(page_path)}">
    <input type="hidden" name="page_title" value="{escape(page_title)}">
    <input type="hidden" name="page_url" value="">
    <input type="hidden" name="rendered_at" value="{now_seconds}">
    <input type="hidden" name="submission_token" value="{now_seconds}-{escape(page_path).replace('/', '_')}">
    <div class="sr-only">
      <label for="homepage">Homepage</label>
      <input id="homepage" name="homepage" type="text" tabindex="-1" autocomplete="off">
    </div>
    <div class="actions">
      <button type="submit">Sign the guestbook</button>
      <a href="{escape(self.config.base_path)}/page?path={escape(page_path)}">View comments</a>
      <a href="{escape(self.config.base_path)}/guidelines">How to sign the book</a>
    </div>
  </form>
</section>
<script>
  const form = document.querySelector("form");
  if (form) {{
    const pageUrl = form.querySelector('input[name="page_url"]');
    if (pageUrl) pageUrl.value = window.location.href;
  }}
</script>
"""
        return self.layout("Leave a note", body)

    def page_comments_page(self, page_path: str) -> str:
        with connect(self.config.database_path) as conn:
            entries = fetch_public_entries(conn, page_path=page_path, order=self.config.default_order)
        if entries:
            items = "".join(
                f"<article class='entry'><h2>{escape(row['display_name'])}</h2><p class='meta'>{escape(row['created_utc'])}</p>{row['comment_rendered']}</article>"
                for row in entries
            )
        else:
            items = "<p>No comments yet. Be the first to sign the book for this page.</p>"
        body = f"""
<section class="card">
  <h1>Comments for <code>{escape(page_path)}</code></h1>
  <div class="actions">
    <a href="{escape(self.config.base_path)}/form?path={escape(page_path)}">Leave a note</a>
    <a href="{escape(self.config.base_path)}/all">View the whole book</a>
  </div>
</section>
<section class="card">{items}</section>
"""
        return self.layout("Page comments", body)

    def all_comments_page(self) -> str:
        with connect(self.config.database_path) as conn:
            entries = fetch_public_entries(conn, order=self.config.default_order)
        if entries:
            items = "".join(
                f"<article class='entry'><h2>{escape(row['display_name'])}</h2><p class='meta'>{escape(row['created_utc'])} on <code>{escape(row['page_path'])}</code></p>{row['comment_rendered']}</article>"
                for row in entries
            )
        else:
            items = "<p>No approved notes yet.</p>"
        body = f"""
<section class="card">
  <h1>{escape(self.config.site_name)} guestbook</h1>
  <p class="meta">A page-aware stream of approved notes from across the site.</p>
</section>
<section class="card">{items}</section>
"""
        return self.layout("Guestbook", body)

    def guidelines_page(self) -> str:
        body = """
<section class="card">
  <h1>How to sign the book</h1>
  <p>This guestbook is for sincere remarks, responses, and sightings from fellow travellers.</p>
  <p>Spam, scams, and hostile nonsense are unwelcome. Links may be filtered. Suspicious notes may be held for moderation.</p>
  <p>Markdown is welcome. Raw HTML is not.</p>
</section>
"""
        return self.layout("Guidelines", body)

    def message_page(self, title: str, detail: str, page_path: str = "/") -> str:
        body = f"""
<section class="card">
  <h1>{escape(title)}</h1>
  <p>{escape(detail)}</p>
  <div class="actions">
    <a href="{escape(self.config.base_path)}/page?path={escape(page_path)}">Back to comments</a>
    <a href="{escape(self.config.base_path)}/form?path={escape(page_path)}">Post another note</a>
  </div>
</section>
"""
        return self.layout(title, body)

    def not_found_page(self) -> str:
        return self.layout("Not found", "<section class='card'><h1>Not found</h1></section>")

    def error_page(self) -> str:
        return self.layout("Error", "<section class='card'><h1>Internal error</h1><p>Check the guestbook logs for details.</p></section>")


def configure_logging(config: Config) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if config.log_file:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
    )


def build_app(config_path: str | Path | None = None) -> GuestbookApp:
    config = load_config(config_path)
    init_db(config.database_path)
    configure_logging(config)
    return GuestbookApp(config)


def serve(config_path: str | Path | None = None) -> None:
    app = build_app(config_path)
    with make_server(app.config.bind_host, app.config.bind_port, app) as server:
        app.logger.info("serving guestbook on %s:%s", app.config.bind_host, app.config.bind_port)
        server.serve_forever()

