"""Pattern parsing, keyword substitution, and dataview row builders."""

import re
from typing import Optional

DEFAULT_PATTERNS = """title
[title](url)
title - url
url
surl
title - surl
[title](surl)
=HYPERLINK("url", "title")"""

_KEYWORD_RE = re.compile(r"title|surl|url")


def parse_patterns(raw: str) -> list[str]:
    """Parse newline-separated patterns, skipping empty lines and # comments."""
    source = raw.strip() if raw and raw.strip() else DEFAULT_PATTERNS
    result = []
    for line in source.splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        result.append(item)
    return result


def pattern_needs_surl(pattern: str) -> bool:
    return "surl" in pattern


def any_pattern_needs_surl(patterns: list[str]) -> bool:
    return any(pattern_needs_surl(p) for p in patterns)


def format_pattern(pattern: str, title: str, url: str, surl: str = "") -> str:
    """Single-pass keyword substitution so values containing 'url' aren't corrupted."""
    mapping = {
        "title": title,
        "surl": surl,
        "url": url,
    }
    return _KEYWORD_RE.sub(lambda m: mapping[m.group(0)], pattern)


def build_rows(
    patterns: list[str],
    title: str,
    url: str,
    service: str,
    surl: Optional[str] = None,
    shorten_error: Optional[str] = None,
) -> list[dict[str, str]]:
    """Build Alfred UI dataview rows with live previews and metadata."""
    rows: list[dict[str, str]] = []
    for idx, pattern in enumerate(patterns):
        needs_surl = pattern_needs_surl(pattern)
        if needs_surl:
            if surl:
                preview = format_pattern(pattern, title, url, surl)
                badge = f"Shortened ({service}) · {len(preview)} chars"
            elif shorten_error:
                preview = format_pattern(pattern, title, url, f"<shorten failed: {shorten_error}>")
                badge = f"{service} failed"
            else:
                preview = format_pattern(pattern, title, url, f"<shortening via {service}…>")
                badge = f"Shortening via {service}…"
        else:
            preview = format_pattern(pattern, title, url)
            badge = f"{len(preview)} chars"

        rows.append(
            {
                "uid": f"pattern-{idx}",
                "row_pattern.text": pattern,
                "row_preview.text": preview,
                "pattern": pattern,
                "preview": preview,
                "badge": badge,
                "keywords": f"{pattern} {preview}",
            }
        )
    return rows
