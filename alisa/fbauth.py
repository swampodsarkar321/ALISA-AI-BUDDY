"""ALISA accounts: username/password login via Firebase Auth (REST, no deps).

Usernames map to synthetic emails (name@alisa.local) — users only ever
type a username + password. Session cached locally for offline use.
"""

import json
import re
import time
import urllib.error
import urllib.request

# Public web key (safe to embed — access enforced by Auth + DB rules).
WEB_API_KEY = "AIzaSyCwpylnjqWQLBpgoiStlrE01o95aKP3JSY"
DB_URL = "https://chat-2-me-c3213-default-rtdb.firebaseio.com"
IDENTITY = "https://identitytoolkit.googleapis.com/v1/accounts"
SECURETOKEN = "https://securetoken.googleapis.com/v1/token"


def to_email(username):
    clean = re.sub(r"[^a-z0-9]", "", (username or "").lower()) or "user"
    return f"{clean}@alisa.local"


def _post(url, payload, timeout=15):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r), None
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e)
            msg = err.get("error", {}).get("message", f"HTTP {e.code}")
        except Exception:
            msg = f"HTTP {e.code}"
        return None, msg
    except Exception as e:
        return None, f"Network error: {e}"


def _friendly(code):
    code = (code or "").split(":")[0].strip()
    return {
        "EMAIL_EXISTS": "This username is taken — try Login instead.",
        "OPERATION_NOT_ALLOWED": "Login is not enabled yet. Contact support.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many tries — wait a bit and retry.",
        "EMAIL_NOT_FOUND": "No such user — Register first.",
        "INVALID_PASSWORD": "Wrong password. Try again.",
        "INVALID_LOGIN_CREDENTIALS": "Wrong username or password.",
        "USER_DISABLED": "This account is disabled. Contact support.",
        "WEAK_PASSWORD": "Password must be 6+ characters.",
    }.get(code, f"Login failed: {code}")


def _need_key():
    if not WEB_API_KEY:
        return "Login not configured yet. Contact support."
    return ""


def signup(username, password):
    missing = _need_key()
    if missing:
        return None, missing
    if len(password or "") < 6:
        return None, "Password must be 6+ characters."
    data, err = _post(f"{IDENTITY}:signUp?key={WEB_API_KEY}",
                      {"email": to_email(username), "password": password,
                       "returnSecureToken": True})
    if err:
        return None, _friendly(err)
    return _session(username, data), ""


def signin(username, password):
    missing = _need_key()
    if missing:
        return None, missing
    data, err = _post(f"{IDENTITY}:signInWithPassword?key={WEB_API_KEY}",
                      {"email": to_email(username), "password": password,
                       "returnSecureToken": True})
    if err:
        return None, _friendly(err)
    return _session(username, data), ""


def _session(username, data):
    return {
        "username": username.strip(),
        "uid": data.get("localId", ""),
        "idToken": data.get("idToken", ""),
        "refreshToken": data.get("refreshToken", ""),
        "expiry": int(time.time()) + int(data.get("expiresIn", 3600)) - 60,
    }


def refresh(session):
    if not session or not session.get("refreshToken"):
        return None
    data, err = _post(f"{SECURETOKEN}?key={WEB_API_KEY}",
                      {"grant_type": "refresh_token",
                       "refresh_token": session["refreshToken"]})
    if err or not data:
        return None
    session.update({
        "idToken": data.get("id_token", session["idToken"]),
        "refreshToken": data.get("refresh_token", session["refreshToken"]),
        "expiry": int(time.time()) + int(data.get("expires_in", 3600)) - 60,
        "uid": data.get("user_id", session.get("uid", "")),
    })
    return session


def valid_session(session):
    """Fresh session or None (caller tries refresh first)."""
    if not session or not session.get("idToken"):
        return None
    if int(session.get("expiry", 0)) > int(time.time()) + 30:
        return session
    return None


def write_user_record(session, extra=None):
    """Save/update this user's row (uses their own login token)."""
    try:
        from .license import device_id
        from .updater import APP_VERSION
        payload = {"name": session.get("username", ""),
                   "device": device_id(),
                   "appVersion": APP_VERSION,
                   "lastSeen": int(time.time())}
        if extra:
            payload.update(extra)
        url = f"{DB_URL}/users/{session['uid']}.json?auth={session['idToken']}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     method="PATCH",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            pass
        return True
    except Exception:
        return False
