"""ALISA knowledge base: owner-taught Q&A, fetched from Firebase (cached).

Matching is offline & instant — the app refreshes the cache in background.
"""

import json
import re
import time
import urllib.request

KB_URL = "https://chat-2-me-c3213-default-rtdb.firebaseio.com/kb.json"
_cache = {"at": 0, "entries": []}


def _normalize(s):
    s = str(s or "")
    # unify Bengali spelling variants (all U+ escapes, no literal chars):
    s = s.replace("\u09df", "\u09af")
    s = s.replace("\u09af\u09bc", "\u09af")
    s = s.replace("\u200c", "").replace("\u200d", "")
    return s


def _words(s):
    s = _normalize(s).lower()
    return [w for w in re.sub(r"[^\w\s\u0980-\u09FF]", " ", s).split()
            if len(w) > 1 or w.isdigit()]


def _score(pattern, text):
    pw, tw = set(_words(pattern)), set(_words(text))
    if not pw:
        return 0.0
    hit = pw & tw
    if not hit:
        return 0.0
    cov = len(hit) / len(pw)
    if cov >= 0.6:
        return cov
    # one strong word (e.g. a name like Jewel) is enough to match
    if max(len(w) for w in hit) >= 4:
        return 0.65
    return cov


def find_answer(text, entries):
    best, best_score = None, 0.6
    for e in entries or []:
        if not isinstance(e, dict) or not e.get("answer"):
            continue
        patterns = e.get("patterns", [])
        if isinstance(patterns, str):
            patterns = [patterns]
        for p in patterns:
            s = _score(p, text)
            if s > best_score:
                best, best_score = e, s
    return best["answer"].strip() if best else None


def cached_entries():
    if _cache["entries"]:
        return _cache["entries"]
    try:
        from . import config as _cfg
        saved = _cfg.load().get("kb_cache", {})
        if isinstance(saved.get("entries"), list):
            _cache["entries"] = saved["entries"]
            _cache["at"] = saved.get("at", 0)
    except Exception:
        pass
    return _cache["entries"]


def refresh():
    """Fetch latest KB (owner edits). Returns entry count."""
    try:
        with urllib.request.urlopen(KB_URL, timeout=10) as r:
            data = json.load(r) or {}
        entries = [v for v in data.values() if isinstance(v, dict) and v.get("answer")]
        _cache["entries"] = entries
        _cache["at"] = int(time.time())
        try:
            from . import config as _cfg
            d = _cfg.load()
            d["kb_cache"] = {"at": _cache["at"], "entries": entries}
            _cfg.save(d)
        except Exception:
            pass
        return len(entries)
    except Exception:
        return len(cached_entries())
