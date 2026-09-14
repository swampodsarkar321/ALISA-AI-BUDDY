"""ALISA AI clients: Gemini (primary) + OpenRouter (fallback), text + vision."""

import json
import re
import time
import urllib.request

try:
    import google.generativeai as genai
    _GENAI = True
except Exception:
    _GENAI = False

SYSTEM_PROMPT = (
    "You are ALISA, a friendly offline-first Windows desktop assistant. "
    "Your creator is Swampod Sarkar — if anyone asks who made/created/developed you, "
    "answer: Swampod Sarkar. "
    "Answer briefly (under 80 words unless asked for detail). "
    "You can open apps, control volume/brightness, search the web and save notes."
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Best free models in priority order — auto-switches on failure/rate-limit.
OPENROUTER_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "google/gemma-4-26b-a4b-it:free",
    "liquid/lfm-2.5-2.6b:free",
]
OPENROUTER_MODEL = OPENROUTER_MODELS[1]  # default display name
OPENROUTER_VISION_MODEL = "inclusionai/ling-3.0-flash-vl:free"

# ── Built-in key: XOR-obfuscated + split (stops casual `strings` theft) ───────
# Primary source is Firebase meta/appconfig (owner rotates without rebuild).
# Fallback below is only for offline/first-run.
_XOR = 0x5A
_KPARTS = [
    '2931773528772c6b776d3e6d683f6a',
    '623e38393c396368623969393f386a',
    '3c6f3b6f6f6a6d396b6e3f6a6e6b6b',
    '386d6a3f383b3c6f39683b6e3c686a',
    '6e3962686f636b623c386c6863',
]
_APPCONFIG_URL = ("https://chat-2-me-c3213-default-rtdb.firebaseio.com"
                  "/meta/appconfig.json")
_remote_key_cache = {"key": "", "at": 0}


def _builtin_key():
    try:
        raw = "".join(_KPARTS)
        return bytes(int(raw[i:i + 2], 16) ^ _XOR
                     for i in range(0, len(raw), 2)).decode()
    except Exception:
        return ""


def _remote_key():
    """Owner-rotatable key from Firebase (cached 24h locally)."""
    import time as _t
    now = _t.time()
    if _remote_key_cache["key"] and now - _remote_key_cache["at"] < 86400:
        return _remote_key_cache["key"]
    try:
        from . import config as _cfg
        saved = _cfg.load().get("appkey", {})
        if saved.get("key") and now - saved.get("at", 0) < 86400:
            _remote_key_cache.update(key=saved["key"], at=saved["at"])
            return saved["key"]
    except Exception:
        pass
    try:
        import urllib.request as _u
        import json as _j
        with _u.urlopen(_APPCONFIG_URL, timeout=8) as r:
            data = _j.load(r) or {}
        key = clean_or_key(data.get("orKey", ""))
        if key:
            _remote_key_cache.update(key=key, at=now)
            try:
                from . import config as _cfg2
                d = _cfg2.load()
                d["appkey"] = {"key": key, "at": now}
                _cfg2.save(d)
            except Exception:
                pass
            return key
    except Exception:
        pass
    return ""


def DEFAULT_OR_KEY():
    return _remote_key() or _builtin_key()


def _assert_free(model):
    if not model.endswith(":free"):
        raise RuntimeError("Only free (:free) models are allowed in ALISA.")


def clean_or_key(k):
    """Extract a valid key, else '' (caller falls back to built-in key)."""
    m = re.search(r"sk-or-v1-[A-Za-z0-9\-_]+", k or "")
    return m.group(0) if m else ""


class GeminiClient:
    """Default: OpenRouter free models (no setup needed). Gemini = optional upgrade."""

    def __init__(self, api_key="", or_key=""):
        self.api_key = (api_key or "").strip()
        self._explicit = clean_or_key(or_key)
        self._memo = None
        self._model = None

    def _key(self, remote=True):
        """Explicit key → Firebase remote key → built-in fallback. Memoized."""
        if self._explicit:
            return self._explicit
        if self._memo:
            return self._memo
        if remote:
            k = _remote_key()
            if k:
                self._memo = k
                return k
        return _builtin_key()

    @property
    def ready(self):
        return bool(self._explicit or _builtin_key() or (_GENAI and self.api_key))

    @property
    def provider(self):
        if self._explicit or _builtin_key():
            return "OpenRouter-free"
        if _GENAI and self.api_key:
            return "Gemini"
        return "off"

    def _ensure(self):
        if not _GENAI:
            raise RuntimeError("Install the AI package: pip install google-generativeai")
        if not self.api_key:
            raise RuntimeError("No API key — add your free Gemini key in Settings.")
        if self._model is None:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(
                "gemini-2.0-flash", system_instruction=SYSTEM_PROMPT
            )
        return self._model

    def _with_facts(self, prompt, facts):
        if facts:
            return "Facts you remember about the user:\n- " + "\n- ".join(facts) + f"\n\nUser: {prompt}"
        return prompt

    def ask(self, prompt, history=None, facts=None):
        # OpenRouter free models first (zero setup) → Gemini fallback.
        if self._key():
            try:
                return self._ask_openrouter(prompt, facts, history)
            except Exception as e:
                if not (_GENAI and self.api_key):
                    raise RuntimeError(f"AI error: {e}")
        model = self._ensure()
        chat = model.start_chat(history=history or [])
        resp = chat.send_message(self._with_facts(prompt, facts))
        return ((resp.text or "").strip()) or "(empty reply)"

    def _ask_openrouter(self, prompt, facts=None, history=None):
        if not self._key():
            raise RuntimeError("AI error — check your API key in Settings.")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if facts:
            messages.append({"role": "system", "content": "Remembered facts: " + "; ".join(facts)})
        for m in (history or [])[-6:]:
            role = "assistant" if m.get("role") == "model" else "user"
            parts = m.get("parts", [""])
            messages.append({"role": role, "content": parts[0] if parts else ""})
        messages.append({"role": "user", "content": prompt})
        last_err = "unknown error"
        for model in OPENROUTER_MODELS:
            _assert_free(model)
            payload = json.dumps({"model": model, "messages": messages}).encode()
            try:
                req = urllib.request.Request(
                    OPENROUTER_URL, data=payload,
                    headers={"Authorization": f"Bearer {self._key()}",
                             "Content-Type": "application/json",
                             "HTTP-Referer": "https://localhost/alisa",
                             "X-Title": "ALISA Assistant"},
                )
                with urllib.request.urlopen(req, timeout=45) as r:
                    data = json.load(r)
                choices = (data or {}).get("choices") or []
                if choices and choices[0].get("message", {}).get("content"):
                    return choices[0]["message"]["content"].strip()
                last_err = str((data or {}).get("error", {}).get("message", "empty reply"))[:120]
            except Exception as e:
                last_err = str(e)[:120]
            time.sleep(1)
        raise RuntimeError(f"AI busy ({last_err}). Try again in a moment.")

    def describe_image(self, jpeg_bytes, prompt="Describe what you see briefly."):
        """Vision: OpenRouter free vision model first, Gemini as fallback."""
        if self._key():
            try:
                return self._describe_image_or(jpeg_bytes, prompt)
            except Exception as e:
                if not (_GENAI and self.api_key):
                    raise RuntimeError(f"Vision error: {e}")
        model = self._ensure()
        resp = model.generate_content([
            {"mime_type": "image/jpeg", "data": jpeg_bytes},
            prompt,
        ])
        return (resp.text or "").strip() or "(could not describe image)"

    def _describe_image_or(self, jpeg_bytes, prompt):
        import base64
        _assert_free(OPENROUTER_VISION_MODEL)
        b64 = base64.b64encode(jpeg_bytes).decode()
        payload = json.dumps({
            "model": OPENROUTER_VISION_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
        }).encode()
        req = urllib.request.Request(
            OPENROUTER_URL, data=payload,
            headers={"Authorization": f"Bearer {self._key()}",
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://localhost/alisa",
                     "X-Title": "ALISA Assistant"},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"].strip()
