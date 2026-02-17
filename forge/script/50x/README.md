# 50x Deployment Notes

## Deploy

Copy to web root:

- `50x.html` -> `/srv/www/st33v.com/50x.html`
- `50x.css` -> `/srv/www/st33v.com/50x.css`
- `assets/50x.png` -> `/srv/www/st33v.com/assets/50x.png`

## Nginx config

In the correct `server {}` block:

```nginx
error_page 500 502 503 504 /50x.html;

location = /50x.html {
    # internal;  # optional: uncomment if you only want it served as an error handler
}
```

This is the canonical pattern used in nginx examples.
