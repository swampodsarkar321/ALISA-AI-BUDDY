"""ALISA in-app update channel (Firebase-hosted appcast, no server needed).

Owner publishes a release by setting this node in Firebase Console:
  meta/appcast = {
    "version": "1.1.0",
    "notes": "What's new:\\n- faster voice\\n- new tools",
    "url": "https://github.com/swampodsarkar321/ALISA-AI-BUDDY/releases"
  }
Rules needed once: {"rules": {"meta": {".read": true}, ...}}
"""

import json
import urllib.request

APP_VERSION = "1.0.1"
APPCAST_URL = "https://chat-2-me-c3213-default-rtdb.firebaseio.com/meta/appcast.json"


def _parse_version(v):
    parts = []
    for p in str(v or "").strip().lstrip("vV").split("."):
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer(latest, current):
    a, b = _parse_version(latest), _parse_version(current)
    length = max(len(a), len(b))
    a += (0,) * (length - len(a))
    b += (0,) * (length - len(b))
    return a > b


def check_update():
    """Returns dict(update, current, latest, notes, url) or None when offline/empty."""
    try:
        with urllib.request.urlopen(APPCAST_URL, timeout=10) as r:
            data = json.load(r)
        if not data or not data.get("version"):
            return None
        latest = str(data["version"])
        if not is_newer(latest, APP_VERSION):
            return {"update": False, "current": APP_VERSION, "latest": latest}
        return {
            "update": True,
            "current": APP_VERSION,
            "latest": latest,
            "notes": str(data.get("notes", "Bug fixes and improvements.")),
            "url": str(data.get("url", "https://github.com/swampodsarkar321/ALISA-AI-BUDDY/releases")),
        }
    except Exception:
        return None
