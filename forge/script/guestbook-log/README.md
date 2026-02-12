# nginx-digest

Generate a daily UTC markdown digest from nginx access logs and email it via msmtp.

## Install layout (remote server)
- Code: `/opt/nginx-digest/` (this repo)
- Reports: `/home/st33v/nginx-digest/daily/`
- Systemd units: `/etc/systemd/system/`

## Configuration
Create `/etc/nginx/nginx-digest.conf`:

```bash
RECIPIENT="you@yourdomain"
SENDER="nginx-digest@st33v.com"
SUBJECT_PREFIX="nginx digest"
```

`send_report.sh` expects `msmtp` to be installed and configured. Example `.msmtprc` location: `/home/st33v/.msmtprc` or `/root/.msmtprc` depending on which user runs the service.

## Log format assumptions
The parser expects nginx **combined** log format:

```
$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
```

Input files:
- `/var/log/nginx/access.log`
- Optional rotated `/var/log/nginx/access.log.1`

## Report window
Yesterday in UTC.

## What’s in the report
- Totals: requests, unique visitors, page views, plays
- Top 10 tracks (by plays)
- Top 10 pages (by hits)
- Top referrers
- Notable bots/scanners (from `bots.txt`)
- Top 10 404 paths

Definitions:
- Visitor: unique `(ip, user_agent)`
- Play: audio request with extension in `{mp3, ogg, opus, m4a, flac, wav, aac}`, status `200` or `206`, deduped as 1 play per `(ip, user_agent, url_path)` per day
- Page view: non-audio `GET` request with status `200` (basic asset filtering applied)

## Manual test
Run locally on the server:

```bash
/opt/nginx-digest/nginx_digest.py
cat /home/st33v/nginx-digest/daily/$(date -u -d "yesterday" +%F).md
/opt/nginx-digest/send_report.sh
```

## Systemd
Copy unit files:

```
cp /opt/nginx-digest/systemd/nginx-digest.service /etc/systemd/system/
cp /opt/nginx-digest/systemd/nginx-digest.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now nginx-digest.timer
```
