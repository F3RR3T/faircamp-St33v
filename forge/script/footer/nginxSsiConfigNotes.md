# Nginx SSI Config Notes

## Injection Decision (WO-1)
- Observed on real stage output: all sampled and scanned files include both `<footer>...</footer>` and `</body>`.
- Decision: inject by replacing existing `<footer>...</footer>` first.
- Fallback: if no footer is found, insert SSI include immediately before `</body>`.

SSI include line used by injector:

```html
<!--#include virtual="/include/footerInclude.html" -->
```

## File Placement
- Deploy shared fragment to: `/srv/www/include/footerInclude.html` (adjacent to `/srv/www/st33v.com`).
- Expose it via nginx at URL path `/include/footerInclude.html`.
- Keep generated pages in `stage/` containing only the SSI include hook.
- Expected run mode: in-place injection without backups (default), because Faircamp regeneration is the source of truth.

## Minimal Nginx Example

```nginx
server {
    server_name st33v.com;
    root /srv/www/st33v.com;

    # Adjacent shared include area (not touched by stage rsync --delete)
    location /include/ {
        alias /srv/www/include/;
    }

    location / {
        index index.html;
        ssi on;
        ssi_types text/html;
    }
}
```

## Validation Checklist
1. Set a distinctive token in `/srv/www/include/footerInclude.html` (example: `SSI-FOOTER-OK`).
2. Reload nginx (`nginx -t` then `systemctl reload nginx`).
3. Confirm token appears on:
- `/`
- one album page (example `/colloquium/`)
- one `sotd` page (example `/sotd/2026-02-26-hyphae/`)
4. View page source and verify the SSI comment exists in generated HTML while the rendered page shows expanded footer content.

## Caching / Compression Notes
- SSI modifies response bodies at serve time. Validate interactions with any reverse proxy cache.
- Keep `footerInclude.html` cache TTL short (or purge) so footer updates propagate quickly.
- Gzip usually still works with SSI; keep defaults unless you see incorrect output.

## Safety Switch
- Immediate stop: set `ssi off;` in the serving location and reload nginx.
- Alternate stop: deploy HTML without SSI hooks (or run rollback restore from backups).
