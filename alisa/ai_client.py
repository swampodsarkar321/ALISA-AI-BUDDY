"""ALISA AI clients: Gemini (primary) + OpenRouter (fallback), text + vision."""

import json
import re
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
OPENROUTER_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
OPENROUTER_VISION_MODEL = "inclusionai/ling-3.0-flash-vl:free"

# No built-in key (never commit secrets!): paste your free key in
# ALISA Settings, or set it once and it stays saved on your PC.
DEFAULT_OR_KEY = ""


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
        self.or_key = clean_or_key(or_key) or DEFAULT_OR_KEY
        self._model = None

    @property
    def ready(self):
        return bool(self.or_key or (_GENAI and self.api_key))

    @property
    def provider(self):
        if self.or_key:
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
        if self.or_key:
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
        if not self.or_key:
            raise RuntimeError("AI error — check your API key in Settings.")
        _assert_free(OPENROUTER_MODEL)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if facts:
            messages.append({"role": "system", "content": "Remembered facts: " + "; ".join(facts)})
        for m in (history or [])[-6:]:
            role = "assistant" if m.get("role") == "model" else "user"
            parts = m.get("parts", [""])
            messages.append({"role": role, "content": parts[0] if parts else ""})
        messages.append({"role": "user", "content": prompt})
        payload = json.dumps({"model": OPENROUTER_MODEL, "messages": messages}).encode()
        req = urllib.request.Request(
            OPENROUTER_URL, data=payload,
            headers={"Authorization": f"Bearer {self.or_key}",
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://localhost/alisa",
                     "X-Title": "ALISA Assistant"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"].strip()

    def describe_image(self, jpeg_bytes, prompt="Describe what you see briefly."):
        """Vision: OpenRouter free vision model first, Gemini as fallback."""
        if self.or_key:
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
            headers={"Authorization": f"Bearer {self.or_key}",
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://localhost/alisa",
                     "X-Title": "ALISA Assistant"},
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"].strip()
