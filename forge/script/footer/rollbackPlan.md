# Rollback Plan

## Fastest Stopgap
1. Disable SSI in nginx (`ssi off;`) for HTML location.
2. Reload nginx.

This immediately stops include expansion and stabilizes behavior while preserving deployed files.

## File Rollback (In-Place Injection)
This only applies when you used `--backup`. If `injectFooterSsiHook` wrote `.bak` files:

```bash
./injectFooterSsiHook /home/st33v/dox/st33v.com/stage --revert
```

That restores all `*.html.bak` files back to original `*.html`.

## Full Rebuild Rollback
1. Re-run normal Faircamp stage build to regenerate clean `stage/` (primary rollback path).
2. Skip SSI injection step.
3. Rsync clean `stage/` to server.

## Verification After Rollback
1. Open `/` and one deep page (for example `/colloquium/1/`).
2. Confirm Faircamp footer is back and SSI token is absent.
3. Confirm no broken markup near end of body.
