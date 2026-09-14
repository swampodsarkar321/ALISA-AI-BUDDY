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

def check_announcement():
    """Returns {id, title, body} or None."""
    try:
        with urllib.request.urlopen(
            "https://chat-2-me-c3213-default-rtdb.firebaseio.com/meta/announcement.json",
            timeout=10,
        ) as r:
            data = json.load(r)
        if not data or not data.get("id"):
            return None
        return {"id": str(data["id"]), "title": str(data.get("title", "Notice")),
                "body": str(data.get("body", ""))}
    except Exception:
        return None


def is_exe_update(url):
    return str(url or "").lower().split("?")[0].endswith(".exe")


def download_update(url, dest_path, progress_cb=None):
    """Download with progress. progress_cb(downloaded, total)."""
    import os as _os
    req = urllib.request.Request(url, headers={"User-Agent": "ALISA-Updater"})
    with urllib.request.urlopen(req, timeout=120) as r:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if progress_cb:
                    try:
                        progress_cb(got, total)
                    except Exception:
                        pass
    if total and _os.path.getsize(dest_path) != total:
        raise RuntimeError("Download incomplete — try again.")
    return dest_path


def apply_update(new_exe_path):
    """Swap running exe with the downloaded one and restart (frozen only).

    Returns True if the updater was launched (caller must exit immediately).
    """
    import os as _os
    import subprocess as _sp
    import sys as _sys
    if not getattr(_sys, "frozen", False):
        return False
    current = _sys.executable
    bat = os.path.join(_os.path.expandvars("%TEMP%"), "alisa-update.bat")
    with open(bat, "w", encoding="utf-8") as f:
        f.write(
            "@echo off\n"
            "timeout /t 4 /nobreak >nul\n"
            f'move /y "{current}" "{current}.bak" >nul\n'
            f'move /y "{new_exe_path}" "{current}" >nul\n'
            f'if not exist "{current}" ( move /y "{current}.bak" "{current}" >nul )\n'
            f'if exist "{current}" ( del "{current}.bak" >nul 2>&1 )\n'
            f'start "" "{current}"\n'
            "del \"%~f0\"\n"
        )
    _sp.Popen(["cmd", "/c", bat], creationflags=0x00000008,
              stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
    return True
