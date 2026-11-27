"""Save a URL as a macOS .webloc file in the frontmost Finder or QSpace window via fmctl."""

import os
import plistlib
import re
import shutil
import subprocess
import urllib.parse
from typing import Optional

from browser import list_ordered_apps

# bundle_id -> (fmctl --app value, display name)
FILE_MANAGERS: dict[str, tuple[str, str]] = {
    "com.jinghaoshe.qspace.pro": ("qspace-pro", "QSpace Pro"),
    "com.jinghaoshe.qspace": ("qspace", "QSpace"),
    "com.apple.finder": ("finder", "Finder"),
}

_FMCTL_SEARCH_PATHS = (
    os.path.expanduser("~/.local/bin/fmctl"),
    "/opt/homebrew/bin/fmctl",
    "/usr/local/bin/fmctl",
    os.path.expanduser("~/go/bin/fmctl"),
)

_INVALID_FILENAME_RE = re.compile(r'[/\\:\x00-\x1f]+')
_WHITESPACE_RE = re.compile(r"\s+")


def find_fmctl() -> Optional[str]:
    """Locate the fmctl binary even under Alfred's minimal PATH."""
    configured = os.environ.get("fmctl_path", "").strip()
    if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
        return configured

    found = shutil.which("fmctl")
    if found:
        return found

    for candidate in _FMCTL_SEARCH_PATHS:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _ordered_file_managers() -> list[tuple[str, str]]:
    """Return running supported file managers in macOS window Z-order."""
    data = list_ordered_apps()
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for bucket in ("onScreen", "allWins", "running"):
        for app in data.get(bucket, []):
            bid = app.get("bundleId", "")
            if bid in FILE_MANAGERS and bid not in seen:
                seen.add(bid)
                ordered.append(FILE_MANAGERS[bid])
    return ordered


def _query_fmctl_cwd(fmctl: str, app_arg: str) -> Optional[str]:
    proc = subprocess.run(
        [fmctl, "cwd", "--app", app_arg],
        capture_output=True,
        text=True,
        timeout=4,
    )
    if proc.returncode != 0:
        return None
    path = proc.stdout.strip()
    if path and os.path.isdir(path):
        return path
    return None


def _finder_insertion_location() -> Optional[str]:
    """Fallback when fmctl is unavailable: query Finder insertion location via AppleScript."""
    script = 'tell application "Finder" to POSIX path of (insertion location as alias)'
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except subprocess.SubprocessError:
        return None
    if proc.returncode != 0:
        return None
    path = proc.stdout.strip()
    return path if path and os.path.isdir(path) else None


def detect_target_directory() -> tuple[str, str]:
    """Return (directory_path, source_label) for the frontmost Finder or QSpace window."""
    fmctl = find_fmctl()
    if fmctl:
        for app_arg, label in _ordered_file_managers():
            cwd = _query_fmctl_cwd(fmctl, app_arg)
            if cwd:
                return cwd, label

    finder_dir = _finder_insertion_location()
    if finder_dir:
        return finder_dir, "Finder"

    desktop = os.path.expanduser("~/Desktop")
    return desktop, "Desktop"


def sanitize_filename(title: str, url: str, max_length: int = 120) -> str:
    """Create a safe macOS filename stem from a page title or URL."""
    base = (title or "").strip()
    if not base and url:
        parsed = urllib.parse.urlparse(url)
        base = (parsed.netloc + parsed.path).strip("/") or url
    base = _INVALID_FILENAME_RE.sub("-", base)
    base = _WHITESPACE_RE.sub(" ", base).strip(" .")
    if len(base) > max_length:
        base = base[:max_length].rstrip(" .")
    return base or "bookmark"


def save_webloc(title: str, url: str, directory: str) -> str:
    """Write a standard macOS .webloc XML plist file and return its full path."""
    if not url:
        raise ValueError("URL is empty")
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Target directory does not exist: {directory}")

    stem = sanitize_filename(title, url)
    candidate = os.path.join(directory, f"{stem}.webloc")
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{stem} ({counter}).webloc")
        counter += 1

    with open(candidate, "wb") as f:
        plistlib.dump({"URL": url}, f, fmt=plistlib.FMT_XML)

    return candidate
