from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode
import unittest

from guestbook.app import build_app
from guestbook.config import load_config
from guestbook.db import connect, get_entry, init_db, list_entries


def make_config(tmp: str) -> Path:
    root = Path(tmp)
    (root / "config").mkdir()
    (root / "data").mkdir()
    (root / "config" / "blocklist.txt").write_text("telegram me\ncrypto giveaway\n", encoding="utf-8")
    (root / "config" / "profanity.txt").write_text("damn\n", encoding="utf-8")
    (root / "config" / "config.toml").write_text(
        """
[app]
site_name = "test"
bind_host = "127.0.0.1"
bind_port = 8049
base_path = "/guestbook"
secret_key = "test-secret"
default_order = "newest"
require_acknowledgement = false

[paths]
database_path = "data/guestbook.db"
blocklist_path = "config/blocklist.txt"
profanity_path = "config/profanity.txt"

[limits]
max_name_length = 80
min_comment_length = 2
max_comment_length = 4000
cooldown_seconds = 30
max_per_hour = 5
max_per_day = 20
max_urls = 3
max_uppercase_ratio = 0.45

[moderation]
mode = "score"
auto_approve_score = 1
auto_reject_score = 6
blocked_url_domains = ["bit.ly"]

[logging]
level = "CRITICAL"
""".strip(),
        encoding="utf-8",
    )
    return root / "config" / "config.toml"


def wsgi_call(app, path: str, method: str = "GET", body: bytes = b"", remote_addr: str = "127.0.0.1"):
    status_headers = {}

    def start_response(status, headers):
        status_headers["status"] = status
        status_headers["headers"] = headers

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
        "REMOTE_ADDR": remote_addr,
        "HTTP_USER_AGENT": "unittest",
        "HTTP_ACCEPT_LANGUAGE": "en",
    }
    if "?" in path:
        environ["PATH_INFO"], environ["QUERY_STRING"] = path.split("?", 1)
    payload = b"".join(app(environ, start_response))
    return status_headers["status"], dict(status_headers["headers"]), payload.decode("utf-8")


class GuestbookTests(unittest.TestCase):
    def test_valid_submission_is_approved(self):
        with TemporaryDirectory() as tmp:
            config_path = make_config(tmp)
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                app = build_app(config_path)
                form = urlencode(
                    {
                        "display_name": "steve",
                        "comment": "hello **world**",
                        "page_path": "/song/test",
                        "page_title": "Song",
                        "page_url": "https://example.com/song/test",
                        "rendered_at": "1",
                        "homepage": "",
                    }
                ).encode("utf-8")
                status, _, body = wsgi_call(app, "/guestbook/submit", method="POST", body=form)
                self.assertEqual(status, "200 OK")
                self.assertIn("Note posted", body)
                cfg = load_config(config_path)
                with connect(cfg.database_path) as conn:
                    rows = list_entries(conn)
                self.assertEqual(rows[0]["status"], "approved")
            finally:
                os.chdir(cwd)

    def test_empty_submission_is_rejected(self):
        with TemporaryDirectory() as tmp:
            config_path = make_config(tmp)
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                app = build_app(config_path)
                form = urlencode({"display_name": "", "comment": "", "page_path": "/"}).encode("utf-8")
                status, _, body = wsgi_call(app, "/guestbook/submit", method="POST", body=form)
                self.assertEqual(status, "400 Bad Request")
                self.assertIn("Name is required.", body)
            finally:
                os.chdir(cwd)

    def test_html_is_rejected(self):
        with TemporaryDirectory() as tmp:
            config_path = make_config(tmp)
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                app = build_app(config_path)
                form = urlencode(
                    {
                        "display_name": "steve",
                        "comment": "<script>alert(1)</script>",
                        "page_path": "/song/test",
                        "rendered_at": "1",
                    }
                ).encode("utf-8")
                status, _, _ = wsgi_call(app, "/guestbook/submit", method="POST", body=form)
                self.assertEqual(status, "400 Bad Request")
            finally:
                os.chdir(cwd)

    def test_honeypot_marks_spam(self):
        with TemporaryDirectory() as tmp:
            config_path = make_config(tmp)
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                app = build_app(config_path)
                form = urlencode(
                    {
                        "display_name": "bot",
                        "comment": "hello there",
                        "page_path": "/song/test",
                        "homepage": "spam.example",
                        "rendered_at": "1",
                    }
                ).encode("utf-8")
                status, _, body = wsgi_call(app, "/guestbook/submit", method="POST", body=form)
                self.assertEqual(status, "200 OK")
                self.assertIn("Note rejected", body)
            finally:
                os.chdir(cwd)

    def test_rate_limit_blocks_second_post(self):
        with TemporaryDirectory() as tmp:
            config_path = make_config(tmp)
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                app = build_app(config_path)
                first = urlencode(
                    {
                        "display_name": "one",
                        "comment": "first post",
                        "page_path": "/song/test",
                        "rendered_at": "1",
                    }
                ).encode("utf-8")
                second = urlencode(
                    {
                        "display_name": "two",
                        "comment": "second post",
                        "page_path": "/song/test",
                        "rendered_at": "1",
                    }
                ).encode("utf-8")
                wsgi_call(app, "/guestbook/submit", method="POST", body=first)
                status, _, body = wsgi_call(app, "/guestbook/submit", method="POST", body=second)
                self.assertEqual(status, "429 Too Many Requests")
                self.assertIn("Slow down", body)
            finally:
                os.chdir(cwd)

    def test_blocklist_moves_submission_to_pending(self):
        with TemporaryDirectory() as tmp:
            config_path = make_config(tmp)
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                app = build_app(config_path)
                form = urlencode(
                    {
                        "display_name": "suspicious",
                        "comment": "telegram me for a crypto giveaway",
                        "page_path": "/song/test",
                        "rendered_at": "1",
                    }
                ).encode("utf-8")
                status, _, body = wsgi_call(app, "/guestbook/submit", method="POST", body=form)
                self.assertEqual(status, "200 OK")
                self.assertIn("queued for review", body)
            finally:
                os.chdir(cwd)

    def test_page_association_and_public_listing(self):
        with TemporaryDirectory() as tmp:
            config_path = make_config(tmp)
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                app = build_app(config_path)
                form = urlencode(
                    {
                        "display_name": "steve",
                        "comment": "hello from page",
                        "page_path": "/album/test",
                        "rendered_at": "1",
                    }
                ).encode("utf-8")
                wsgi_call(app, "/guestbook/submit", method="POST", body=form)
                status, _, body = wsgi_call(app, "/guestbook/page?path=%2Falbum%2Ftest")
                self.assertEqual(status, "200 OK")
                self.assertIn("/album/test", body)
                self.assertIn("hello from page", body)
            finally:
                os.chdir(cwd)

    def test_admin_approval_flow(self):
        with TemporaryDirectory() as tmp:
            config_path = make_config(tmp)
            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                app = build_app(config_path)
                form = urlencode(
                    {
                        "display_name": "pending",
                        "comment": "DAMN telegram me",
                        "page_path": "/album/test",
                        "rendered_at": "1",
                    }
                ).encode("utf-8")
                wsgi_call(app, "/guestbook/submit", method="POST", body=form)
                cfg = load_config(config_path)
                with connect(cfg.database_path) as conn:
                    row = list_entries(conn)[0]
                    self.assertEqual(row["status"], "pending")
                    from guestbook.db import set_status

                    set_status(conn, row["id"], "approved", "tester", "manual review")
                with connect(cfg.database_path) as conn:
                    approved = get_entry(conn, row["id"])
                    self.assertEqual(approved["status"], "approved")
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()

