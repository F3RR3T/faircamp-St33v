from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(slots=True)
class Config:
    database_path: Path
    bind_host: str
    bind_port: int
    site_name: str
    base_path: str
    log_level: str
    log_file: Path | None
    secret_key: str
    moderation_mode: str
    default_order: str
    max_name_length: int
    min_comment_length: int
    max_comment_length: int
    require_acknowledgement: bool
    cooldown_seconds: int
    max_per_hour: int
    max_per_day: int
    max_urls: int
    max_uppercase_ratio: float
    blocked_url_domains: tuple[str, ...]
    blocklist_path: Path
    profanity_path: Path
    auto_approve_score: int
    auto_reject_score: int


def _read_text_lines(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return ()
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        values.append(line.casefold())
    return tuple(values)


def load_config(path: str | Path | None = None) -> Config:
    config_path = Path(path or "config/config.toml")
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))

    app = raw.get("app", {})
    limits = raw.get("limits", {})
    moderation = raw.get("moderation", {})
    logging = raw.get("logging", {})
    paths = raw.get("paths", {})

    root = config_path.parent.parent if config_path.parent.name == "config" else config_path.parent
    database_path = Path(paths.get("database_path", root / "data/guestbook.db"))
    log_file_value = logging.get("log_file")
    log_file = Path(log_file_value) if log_file_value else None

    return Config(
        database_path=database_path,
        bind_host=app.get("bind_host", "127.0.0.1"),
        bind_port=int(app.get("bind_port", 8049)),
        site_name=app.get("site_name", "st33v.com"),
        base_path=app.get("base_path", "/guestbook"),
        log_level=logging.get("level", "INFO"),
        log_file=log_file,
        secret_key=app.get("secret_key", "change-me"),
        moderation_mode=moderation.get("mode", "score"),
        default_order=app.get("default_order", "newest"),
        max_name_length=int(limits.get("max_name_length", 80)),
        min_comment_length=int(limits.get("min_comment_length", 2)),
        max_comment_length=int(limits.get("max_comment_length", 4000)),
        require_acknowledgement=bool(app.get("require_acknowledgement", False)),
        cooldown_seconds=int(limits.get("cooldown_seconds", 30)),
        max_per_hour=int(limits.get("max_per_hour", 5)),
        max_per_day=int(limits.get("max_per_day", 20)),
        max_urls=int(limits.get("max_urls", 3)),
        max_uppercase_ratio=float(limits.get("max_uppercase_ratio", 0.45)),
        blocked_url_domains=tuple(moderation.get("blocked_url_domains", [])),
        blocklist_path=Path(paths.get("blocklist_path", root / "config/blocklist.txt")),
        profanity_path=Path(paths.get("profanity_path", root / "config/profanity.txt")),
        auto_approve_score=int(moderation.get("auto_approve_score", 1)),
        auto_reject_score=int(moderation.get("auto_reject_score", 6)),
    )


def load_wordlists(config: Config) -> dict[str, tuple[str, ...]]:
    return {
        "blocklist": _read_text_lines(config.blocklist_path),
        "profanity": _read_text_lines(config.profanity_path),
    }

