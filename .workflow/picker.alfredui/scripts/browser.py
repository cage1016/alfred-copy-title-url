"""Detect the frontmost supported browser on macOS and fetch its active tab."""

import json
import subprocess
from typing import Optional

# bundle_id -> (scripting_family, display_name)
# "webkit"   : current tab of front window -> name, URL
# "chromium" : active tab of front window  -> title, URL
BROWSERS: dict[str, tuple[str, str]] = {
    "dev.serafim.fast": ("chromium", "Yab"),
    "com.apple.Safari": ("webkit", "Safari"),
    "com.apple.SafariTechnologyPreview": ("webkit", "Safari Technology Preview"),
    "com.kagi.kagimacOS": ("webkit", "Orion"),
    "company.thebrowser.Browser": ("chromium", "Arc"),
    "company.thebrowser.dia": ("chromium", "Dia"),
    "com.google.Chrome": ("chromium", "Google Chrome"),
    "com.google.Chrome.canary": ("chromium", "Google Chrome Canary"),
    "com.google.Chrome.beta": ("chromium", "Google Chrome Beta"),
    "org.chromium.Chromium": ("chromium", "Chromium"),
    "com.brave.Browser": ("chromium", "Brave Browser"),
    "com.brave.Browser.beta": ("chromium", "Brave Browser Beta"),
    "com.microsoft.edgemac": ("chromium", "Microsoft Edge"),
    "com.vivaldi.Vivaldi": ("chromium", "Vivaldi"),
    "com.operasoftware.Opera": ("chromium", "Opera"),
    "com.operasoftware.OperaGX": ("chromium", "Opera GX"),
}

_ZORDER_JXA = """
ObjC.import("CoreGraphics");
ObjC.import("AppKit");
const ws = $.NSWorkspace.sharedWorkspace;
const apps = ObjC.unwrap(ws.runningApplications);
const byPid = {};
const running = [];
for (const a of apps) {
  const info = {
    name: ObjC.unwrap(a.localizedName) || "",
    bundleId: ObjC.unwrap(a.bundleIdentifier) || "",
    path: a.bundleURL ? ObjC.unwrap(a.bundleURL.path) : ""
  };
  byPid[a.processIdentifier] = info;
  if (info.bundleId) running.push(info);
}
function orderedApps(option) {
  const raw = $.CGWindowListCopyWindowInfo(option, $.kCGNullWindowID);
  const wins = ObjC.deepUnwrap(ObjC.castRefToObject(raw)) || [];
  const seen = new Set();
  const out = [];
  for (const w of wins) {
    if (w.kCGWindowLayer !== 0) continue;
    const pid = w.kCGWindowOwnerPID;
    if (seen.has(pid)) continue;
    seen.add(pid);
    if (byPid[pid]) out.push(byPid[pid]);
  }
  return out;
}
const onScreen = orderedApps($.kCGWindowListOptionOnScreenOnly | $.kCGWindowListExcludeDesktopElements);
const allWins = orderedApps($.kCGWindowListOptionAll | $.kCGWindowListExcludeDesktopElements);
JSON.stringify({ onScreen, allWins, running });
"""


def list_ordered_apps() -> dict[str, list[dict[str, str]]]:
    """Return running macOS apps grouped by onScreen, allWins (Z-order), and running."""
    try:
        proc = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", _ZORDER_JXA],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        return json.loads(proc.stdout.strip() or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return {}


def detect_frontmost_browser() -> Optional[dict[str, str]]:
    """Return metadata for the frontmost running supported browser, or None."""
    data = list_ordered_apps()
    for bucket in ("onScreen", "allWins", "running"):
        for app in data.get(bucket, []):
            bid = app.get("bundleId", "")
            if bid in BROWSERS:
                family, display_name = BROWSERS[bid]
                return {
                    "bundle_id": bid,
                    "family": family,
                    "name": app.get("name") or display_name,
                    "path": app.get("path") or "",
                }
    return None


def get_active_tab(browser: dict[str, str]) -> tuple[str, str]:
    """Fetch (title, url) from the browser's front window active tab."""
    bid = browser["bundle_id"]
    family = browser["family"]

    if family == "webkit":
        script = (
            "set sep to character id 31\n"
            f'tell application id "{bid}"\n'
            '  if (count of windows) = 0 then return ""\n'
            "  set t to current tab of front window\n"
            "  return (name of t) & sep & (URL of t)\n"
            "end tell"
        )
    else:
        script = (
            "set sep to character id 31\n"
            f'tell application id "{bid}"\n'
            '  if (count of windows) = 0 then return ""\n'
            "  set t to active tab of front window\n"
            "  return (title of t) & sep & (URL of t)\n"
            "end tell"
        )

    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=3,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"Failed to query {browser['name']}")

    raw = proc.stdout.strip()
    if not raw:
        return "", ""
    if "\x1f" in raw:
        title, url = raw.rsplit("\x1f", 1)
        return title.strip(), url.strip()
    return raw, ""
