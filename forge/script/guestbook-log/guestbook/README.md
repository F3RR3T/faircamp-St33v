# st33v Guestbook

Small Python and SQLite guestbook/comment service for a static `nginx` site. It is page-aware, uses low-friction anonymous posting, rejects raw HTML, supports a conservative Markdown subset, applies first-line moderation heuristics, and ships with shell-friendly deployment and admin tooling.

## Architecture

- Static site stays static; `nginx` proxies `/guestbook/` to a local Python WSGI service.
- SQLite stores entries and moderation events outside the web root.
- The SSI footer links into the guestbook form, page view, count endpoint, and global guestbook.
- Admin actions are handled through a CLI instead of exposed HTTP admin routes.

## Project Layout

- [`guestbook/`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/guestbook) application package
- [`migrations/schema.sql`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/migrations/schema.sql) SQLite schema
- [`config/config.example.toml`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/config/config.example.toml) production config template
- [`deploy.sh`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/deploy.sh) VPS deployment script
- [`nginx/st33v-guestbook.conf`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/nginx/st33v-guestbook.conf) reverse-proxy snippet
- [`systemd/st33v-guestbook.service`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/systemd/st33v-guestbook.service) service unit template
- [`examples/footer-include.html`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/examples/footer-include.html) SSI footer example

## Dependencies

- Python 3.11+ with `markdown`, `bleach`, and `PyYAML` available locally.
- `nginx` for reverse proxying.
- `systemd` on the VPS if you want the provided service unit.

## Local Run

1. Review [`config/config.toml`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/config/config.toml).
2. Start the app:

```bash
PYTHONPATH=. python3 -m guestbook
```

3. Open:

```text
http://127.0.0.1:8049/guestbook/form?path=/songs/example
```

## Configuration

Main config is TOML.

- `paths.database_path`: SQLite DB path.
- `paths.blocklist_path`: phrase blocklist file.
- `paths.profanity_path`: profanity/slur wordlist file.
- `app.bind_host` / `app.bind_port`: service listener.
- `app.base_path`: mounted HTTP prefix.
- `app.secret_key`: used for IP hashing.
- `limits.*`: validation and rate-limit thresholds.
- `moderation.auto_approve_score`: score ceiling for auto-approval.
- `moderation.auto_reject_score`: score threshold for spam.
- `moderation.blocked_url_domains`: suspicious domains.
- `logging.log_file`: optional log file path.

## Public Routes

- `GET /guestbook/health`
- `GET /guestbook/form?path=/page/path`
- `POST /guestbook/submit`
- `GET /guestbook/page?path=/page/path`
- `GET /guestbook/count?path=/page/path`
- `GET /guestbook/all`
- `GET /guestbook/guidelines`

## Moderation Defaults

- Raw HTML submissions are rejected.
- Honeypot hits are marked as spam.
- Too-fast submissions, repeated characters, link-heavy posts, blocked domains, blocklist phrases, and low-variety spam patterns increase score.
- Mildly suspicious notes go `pending`.
- Strongly suspicious notes go `spam`.
- Public pages show only `approved` entries.

## Admin Commands

Use `guestbook-admin` after deployment, or [`bin/guestbook-admin`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/bin/guestbook-admin) / `python3 -m guestbook.admin` in the repo.

```bash
guestbook-admin list-pending
guestbook-admin approve 12 --actor steve
guestbook-admin spam 19 --actor steve --notes "honeypot"
guestbook-admin recent --limit 20
guestbook-admin search telegram
guestbook-admin stats
guestbook-admin export --format csv
```

## Deployment

Edit [`config/config.example.toml`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/config/config.example.toml) for the VPS, then run as root:

```bash
APP_ROOT=/opt/st33v-guestbook \
CONFIG_ROOT=/etc/st33v-guestbook \
DATA_ROOT=/var/lib/st33v-guestbook \
LOG_ROOT=/var/log/st33v-guestbook \
RUN_NGINX_TEST=1 \
./deploy.sh
```

What it does:

- creates a dedicated `st33v-guestbook` system user/group by default;
- creates app/config/data/log directories;
- installs Python package files and shell wrappers;
- installs `guestbook-admin` into `/usr/local/bin/`;
- installs config templates and wordlists;
- initializes the SQLite DB if needed;
- installs and restarts the systemd service;
- installs the `nginx` snippet and optionally runs `nginx -t`.

Security defaults:

- `/etc/st33v-guestbook/` is created `root:st33v-guestbook` with mode `0750`
- `config.toml`, `blocklist.txt`, and `profanity.txt` are installed `root:st33v-guestbook` with mode `0640`
- `/var/lib/st33v-guestbook/` and `/var/log/st33v-guestbook/` are owned by `st33v-guestbook:st33v-guestbook`
- the systemd service runs as `st33v-guestbook`

## Nginx Integration

Include [`nginx/st33v-guestbook.conf`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/nginx/st33v-guestbook.conf) from the site server block, then reload `nginx`.

The backend expects `X-Forwarded-For` and the normal `Host` header. Keep the writable DB and logs outside the static deploy tree.

## SSI Footer Integration

Start from [`examples/footer-include.html`](/mnt/olho/dox/st33v.com/forge/script/guestbook-log/guestbook/examples/footer-include.html). It populates the current `window.location.pathname`, points the footer links at the page-specific form and comments view, and fetches the approved count for that page.

## Database and Backup

Preferred production paths:

- code: `/opt/st33v-guestbook/`
- config: `/etc/st33v-guestbook/`
- data: `/var/lib/st33v-guestbook/guestbook.db`
- logs: `/var/log/st33v-guestbook/app.log`

Recommended ownership and modes:

- `/etc/st33v-guestbook/`: `root:st33v-guestbook`, `0750`
- `/etc/st33v-guestbook/config.toml`: `root:st33v-guestbook`, `0640`
- `/var/lib/st33v-guestbook/`: `st33v-guestbook:st33v-guestbook`, `0750`
- `/var/log/st33v-guestbook/`: `st33v-guestbook:st33v-guestbook`, `0750`

Back up:

```bash
sqlite3 /var/lib/st33v-guestbook/guestbook.db ".backup '/var/backups/guestbook-$(date +%F).db'"
tar czf /var/backups/st33v-guestbook-config-$(date +%F).tar.gz /etc/st33v-guestbook
```

## Moderation Workflow

1. Review pending notes with `list-pending`.
2. Approve or mark spam via CLI.
3. Use `search`, `recent`, and `stats` to inspect suspicious activity.
4. Adjust `blocklist.txt`, `profanity.txt`, and score thresholds as needed.

## Manual Smoke Test

1. Start the service and confirm `GET /guestbook/health` returns `ok`.
2. Load `/guestbook/form?path=/test-page`.
3. Submit a normal Markdown comment and confirm it appears on `/guestbook/page?path=/test-page`.
4. Submit raw HTML and confirm it is rejected.
5. Fill the honeypot field manually and confirm the note is blocked.
6. Trigger a pending note with a blocklist phrase, then approve it with the CLI.
7. Confirm the footer count endpoint reflects approved comments.

## Testing

Run:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Coverage includes valid submission, empty submission rejection, HTML rejection, honeypot detection, rate limiting, spam phrase detection, page association, and admin approval flow.

## Troubleshooting

- If the service starts but pages fail, check `journalctl -u st33v-guestbook.service`.
- If all posts are blocked, review rate-limit thresholds and wordlists.
- If comments do not appear, confirm the entry status is `approved`.
- If the footer count is empty, check that `nginx` proxies `/guestbook/count`.
- If the DB is not writable, fix ownership for the configured data directory.

## Upgrade and Rollback

Upgrade by redeploying with the same `deploy.sh` and restarting the service. Back up the SQLite DB and `/etc/st33v-guestbook/` first.

Rollback by restoring the previous app tree, config, and the last DB backup, then restarting the service.

## Retention and Privacy

The service stores IP, hashed IP, user agent, referrer, and moderation flags for abuse handling. These values are not shown publicly. Retention is currently manual; prune or archive rows with CLI exports and SQLite maintenance as needed.
