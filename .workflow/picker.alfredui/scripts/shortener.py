"""URL shortening via is.gd / v.gd using Python stdlib only."""

import os
import urllib.error
import urllib.parse
import urllib.request

ALLOWED_SERVICES = {"is.gd", "v.gd"}


def shorten_url(url: str, service: str = "is.gd", timeout: float = 5.0) -> str:
    """Shorten a URL using is.gd or v.gd and return the shortened URL."""
    if not url:
        raise ValueError("URL is empty")
    svc = service if service in ALLOWED_SERVICES else "is.gd"
    version = os.environ.get("alfred_workflow_version", "dev")
    endpoint = f"https://{svc}/create.php?format=simple&url={urllib.parse.quote(url, safe='')}"
    req = urllib.request.Request(
        endpoint,
        headers={"User-Agent": f"alfred-copy-title-url/{version}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace").strip()
    if not body or body.lower().startswith("error:"):
        raise RuntimeError(body or f"Unexpected response from {svc}")
    return body
