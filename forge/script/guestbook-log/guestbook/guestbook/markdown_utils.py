from __future__ import annotations

import bleach
import markdown


ALLOWED_TAGS = [
    "p",
    "br",
    "em",
    "strong",
    "a",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
]
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "rel"]}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def render_comment(text: str) -> str:
    html = markdown.markdown(
        text,
        extensions=["extra", "nl2br", "sane_lists"],
        output_format="html5",
    )
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return bleach.linkify(cleaned, callbacks=[bleach.callbacks.nofollow])

