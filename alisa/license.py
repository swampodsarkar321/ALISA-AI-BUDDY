"""ALISA offline license system (original design).

How it works: the owner generates keys with a PRIVATE secret
(`python generate_key.py --name Rafi`). The app verifies the HMAC
signature locally — no server needed.

⚠️ SECURITY NOTE for the owner:
- Change OWNER_SECRET below to your own random string BEFORE giving out keys.
- NEVER publish generate_key.py's secret or your generated keys.
- Offline checks stop casual sharing only. Determined users can bypass
  anything stored on their own PC — real enforcement needs a server.
"""

import hashlib
import hmac
import json
import os
import re
import time
import urllib.request

from .config import app_data_dir

# !!! OWNER: replace this with your own long random string, keep it private !!!
OWNER_SECRET = "alisa-demo-secret-change-me-9f3k7q2w"

LICENSE_PATH = os.path.join(app_data_dir(), "license.json")
KEY_RE = re.compile(r"^ALISA-([A-Z2-7]{4})-([A-Z2-7]{4})-([A-Z2-7]{4})-([A-Z2-7]{4})-([A-Z2-7]{4})$")

# Online key registry (Firebase). Only SHA-256 hashes are stored publicly —
# hashes can't be reversed into keys, so public read is safe.
KEY_DB_URL = "https://chat-2-me-c3213-default-rtdb.firebaseio.com/keyHashes"
RECHECK_DAYS = 7

PREMIUM_FEATURES = ("vision", "research", "website")


def _sign(payload):
    return hmac.new(OWNER_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_key(label=""):
    """Owner-side: create a key. `label` is only your private note (not in the key)."""
    import secrets as _secrets
    import base64
    raw = _secrets.token_bytes(12)
    b32 = base64.b32encode(raw).decode().rstrip("=")
    groups = [b32[i:i + 4] for i in range(0, 16, 4)]
    payload = "-".join(groups)
    checksum = _sign(payload)[:4].upper()
    # map checksum hex chars into base32 alphabet
    chk = "".join("ABCDEFGHJKMNPQRSTUVWXYZ23456789"[int(c, 16) % 32] for c in checksum)
    return f"ALISA-{payload}-{chk}"


def verify_key(key):
    key = (key or "").strip().upper()
    m = KEY_RE.match(key)
    if not m:
        return False
    payload = "-".join(m.groups()[:4])
    chk = "".join("ABCDEFGHJKMNPQRSTUVWXYZ23456789"[int(c, 16) % 32] for c in _sign(payload)[:4].upper())
    return chk == m.group(5)


def key_hash(key):
    return hashlib.sha256(key.strip().upper().encode()).hexdigest()


def verify_online(key):
    """Check the online registry. Returns True/False/None (None = offline)."""
    try:
        with urllib.request.urlopen(f"{KEY_DB_URL}/{key_hash(key)}.json", timeout=10) as r:
            data = json.load(r)
        if not data:
            return False
        return not data.get("revoked", False)
    except Exception:
        return None


def load_license():
    try:
        with open(LICENSE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            key = data.get("key", "")
            if verify_key(key):
                return {"plan": "premium", "key": key, "lastCheck": data.get("lastCheck", 0)}
    except (OSError, ValueError):
        pass
    return {"plan": "free", "key": ""}


def save_license(key, checked_now=True):
    try:
        payload = {"key": key}
        if checked_now:
            payload["lastCheck"] = int(time.time())
        with open(LICENSE_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return True
    except OSError:
        return False


def recheck_saved_key():
    """Re-verify the saved key online (cheap, runs at startup in background).

    Returns 'ok' | 'revoked' | 'offline'. Revoked keys are downgraded to free.
    Skips the network entirely if checked within RECHECK_DAYS.
    """
    saved = load_license()
    if saved["plan"] != "premium":
        return "free"
    try:
        age_days = (int(time.time()) - int(saved.get("lastCheck", 0))) / 86400
    except (TypeError, ValueError):
        age_days = RECHECK_DAYS + 1
    if age_days < RECHECK_DAYS:
        return "ok"
    result = verify_online(saved["key"])
    if result is True:
        save_license(saved["key"])
        return "ok"
    if result is False:
        save_license("", checked_now=False)
        try:
            os.remove(LICENSE_PATH)
        except OSError:
            pass
        return "revoked"
    return "offline"


def is_premium():
    return load_license()["plan"] == "premium"


def premium_required(feature):
    return (
        f"🔒 '{feature}' is a PREMIUM feature.\n"
        "Open the Activation Center (top bar) and enter your key to unlock it.",
        False,
    )
