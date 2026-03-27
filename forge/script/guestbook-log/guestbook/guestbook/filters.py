from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from urllib.parse import urlparse

from .config import Config


HTML_PATTERN = re.compile(r"<[a-zA-Z!/][^>]*>")
URL_PATTERN = re.compile(r"https?://[^\s)]+", re.IGNORECASE)
WORD_PATTERN = re.compile(r"[a-zA-Z0-9']+")
REPEATED_CHARS = re.compile(r"(.)\1{7,}")


@dataclass(slots=True)
class FilterResult:
    status: str
    score: int
    flags: list[str]
    notes: str


def normalize_page_path(value: str) -> str:
    if not value:
        return "/"
    parsed = urlparse(value)
    path = parsed.path if parsed.scheme or parsed.netloc else value
    if not path.startswith("/"):
        path = "/" + path
    path = re.sub(r"/{2,}", "/", path)
    return path[:512]


def ip_hash(ip_address: str, secret_key: str) -> str:
    return sha256(f"{secret_key}:{ip_address}".encode("utf-8")).hexdigest()


def has_disallowed_html(text: str) -> bool:
    return bool(HTML_PATTERN.search(text))


def analyze_text(name: str, comment: str, page_path: str, honeypot: str, elapsed_seconds: int, config: Config, wordlists: dict[str, tuple[str, ...]]) -> FilterResult:
    score = 0
    flags: list[str] = []

    lowered = f"{name}\n{comment}".casefold()
    urls = URL_PATTERN.findall(comment)

    if honeypot.strip():
        return FilterResult("spam", 99, ["honeypot"], "hidden field populated")
    if elapsed_seconds >= 0 and elapsed_seconds < 2:
        score += 2
        flags.append("submitted_too_fast")
    if has_disallowed_html(comment):
        return FilterResult("rejected", 99, ["html_rejected"], "raw html rejected")
    if REPEATED_CHARS.search(comment):
        score += 2
        flags.append("repeated_characters")
    if urls and len(urls) > config.max_urls:
        score += 3
        flags.append("too_many_urls")
    if urls:
        suspicious = 0
        for url in urls:
            host = (urlparse(url).hostname or "").casefold()
            if any(host.endswith(domain.casefold()) for domain in config.blocked_url_domains):
                suspicious += 1
        if suspicious:
            score += suspicious * 2
            flags.append("blocked_domain")
    letters = [ch for ch in comment if ch.isalpha()]
    if letters:
        ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
        if ratio > config.max_uppercase_ratio:
            score += 1
            flags.append("uppercase_ratio")

    tokens = [word.casefold() for word in WORD_PATTERN.findall(lowered)]
    for phrase in wordlists.get("blocklist", ()):
        if phrase in lowered:
            score += 2
            flags.append(f"blocklist:{phrase}")
    for phrase in wordlists.get("profanity", ()):
        if phrase in tokens:
            score += 1
            flags.append(f"profanity:{phrase}")

    unique_words = len(set(tokens))
    if tokens and unique_words <= max(2, len(tokens) // 4):
        score += 1
        flags.append("low_token_variety")

    if page_path == "/":
        flags.append("root_page")

    if score >= config.auto_reject_score:
        return FilterResult("spam", score, flags, "high spam score")
    if score > config.auto_approve_score:
        return FilterResult("pending", score, flags, "needs moderation")
    return FilterResult("approved", score, flags, "clean")


def encode_flags(flags: list[str]) -> str:
    return json.dumps(flags, sort_keys=True)
