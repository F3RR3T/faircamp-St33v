# 404 Deployment Notes

## Files and placement

Deploy these paths in your site root:

- `/404.html` -> copy from `forge/script/404/404.html`
- `/assets/404-triptych-wall.png` -> place your 1920x1080 triptych image here

The HTML is self-contained (CSS embedded), so no separate JS/CSS files are required.

## Nginx config

```nginx
error_page 404 /404.html;

location = /404.html {
    # internal;   # enable if you want it only as an error handler
}
```

### Dotfile denial

```nginx
location ~ /\.(env|git|ht) {
    deny all;
}
```

### Optional static asset caching

```nginx
location ~* \.(png|jpg|jpeg|gif|woff2|css|js)$ {
    expires 30d;
    add_header Cache-Control "public, max-age=2592000, immutable";
}
```

## Hardcoded portal targets

- `/eli/`
- `/st33v/`
- `/drmorbius/`
- `/sotd/`
- `/`
