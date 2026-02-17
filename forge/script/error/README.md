# Error Pages (404 + 50x)

This directory contains standalone error pages and assets that are deployed outside the regular site build/publish pipeline.

Reason: if your normal publish path uses `rsync --delete`, files not present in that pipeline can be removed. Keeping these in `/srv/www/error/` and deploying manually avoids accidental deletion.

## Local repo tree

```text
forge/script/error/
  404.html
  50x.html
  50x.css
  README.md
  workorder-404
  workorder-50x
  assets/
    404-triptych-wall.png
    50x.png
```

## Target server tree

```text
/srv/www/error/
  404.html
  50x.html
  50x.css
  assets/
    404-triptych-wall.png
    50x.png
```

## Deploy (manual copy)

```bash
sudo mkdir -p /srv/www/error/assets
```

Copy files with either `scp` or `rsync` (without `--delete`):

```bash
rsync -av ~/dox/st33v.com/forge/script/error/ /srv/www/error/
```

Example with `scp`:

```bash
scp -r ~/dox/st33v.com/forge/script/error/* yourhost:/srv/www/error/
```

## Nginx config

Place inside the correct `server {}` block:

```nginx
error_page 404 /_error/404.html;
error_page 500 502 503 504 /_error/50x.html;

location ^~ /_error/ {
    internal;
    alias /srv/www/error/;
}
```

Optional (if not already defined elsewhere):

```nginx
location ~ /\.(env|git|ht) { deny all; }
```

## Testing

- 404: visit `https://st33v.com/ghost`
- 50x: temporarily add:

```nginx
location = /__test_503 { return 503; }
```

Then reload nginx, visit `/__test_503`, and remove that temporary test location.

## Notes

- `internal` prevents direct public browsing to `/_error/...`; nginx can still use it for `error_page`.
- `alias /srv/www/error/;` maps request path `/_error/...` to files under that directory.
- Ensure nginx can read all files (typical mode `644` files, `755` directories).
