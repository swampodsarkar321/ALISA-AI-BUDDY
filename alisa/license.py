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

# !!! OWNER: replace this with your own long random string, keep it private !!!
OWNER_SECRET = "alisa-demo-secret-change-me-9f3k7q2w"

LICENSE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "license.json")
KEY_RE = re.compile(r"^ALISA-([A-Z2-7]{4})-([A-Z2-7]{4})-([A-Z2-7]{4})-([A-Z2-7]{4})-([A-Z2-7]{4})$")

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


def load_license():
    try:
        with open(LICENSE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            key = data.get("key", "")
            if verify_key(key):
                return {"plan": "premium", "key": key}
    except (OSError, ValueError):
        pass
    return {"plan": "free", "key": ""}


def save_license(key):
    try:
        with open(LICENSE_PATH, "w", encoding="utf-8") as f:
            json.dump({"key": key}, f, indent=2)
        return True
    except OSError:
        return False


def is_premium():
    return load_license()["plan"] == "premium"


def premium_required(feature):
    return (
        f"🔒 '{feature}' is a PREMIUM feature.\n"
        "Open the Activation Center (top bar) and enter your key to unlock it.",
        False,
    )
