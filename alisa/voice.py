"""ALISA voice: offline speech output + optional mic input. Degrades gracefully."""

try:
    import pyttsx3
    _TTS = True
except Exception:
    _TTS = False

try:
    import speech_recognition as sr
    _STT = True
except Exception:
    _STT = False


class Voice:
    def __init__(self):
        self.enabled = True
        self._engine = None

    def _engine_get(self):
        if not _TTS:
            return None
        if self._engine is None:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 175)
        return self._engine

    def speak(self, text):
        self.speak_sync(text, tick=None)

    def speak_sync(self, text, tick=None):
        """Speak word-by-word so the mouth syncs with real audio.

        tick(True) fires as each word starts, tick(False) in gaps.
        """
        if not self.enabled or not text:
            if tick:
                try:
                    tick(False)
                except Exception:
                    pass
            return
        try:
            eng = self._engine_get()
            if eng is None:
                if tick:
                    try:
                        tick(False)
                    except Exception:
                        pass
                return
            for w in str(text).split()[:80]:
                if tick:
                    try:
                        tick(True)
                    except Exception:
                        pass
                eng.say(w + " ")
                eng.runAndWait()
            if tick:
                try:
                    tick(False)
                except Exception:
                    pass
        except Exception:
            try:
                if tick:
                    tick(False)
            except Exception:
                pass

    def set_gender(self, female=True):
        """Pick a female/male voice if available. Returns True on success."""
        try:
            eng = self._engine_get()
            if eng is None:
                return False
            voices = eng.getProperty("voices") or []
            pick = None
            for v in voices:
                name = (getattr(v, "name", "") or "").lower()
                if female and any(k in name for k in
                                  ("female", "zira", "eva", "aria", "samantha", "veena", "heera", "swara")):
                    pick = v
                    break
                if not female and any(k in name for k in
                                      ("male", "david", "mark", "ravi", "hemant", "prabhat")):
                    pick = v
                    break
            if pick is None and voices:
                pick = voices[0] if female else (voices[1] if len(voices) > 1 else voices[0])
            if pick is not None:
                eng.setProperty("voice", pick.id)
                return True
        except Exception:
            pass
        return False

    def listen(self, timeout=6):
        """Returns recognized text or an error message starting with '!'."""
        if not _STT:
            return "! Voice input needs: pip install SpeechRecognition PyAudio"
        try:
            rec = sr.Recognizer()
            with sr.Microphone() as src:
                rec.adjust_for_ambient_noise(src, duration=0.5)
                audio = rec.listen(src, timeout=timeout, phrase_time_limit=12)
            return rec.recognize_google(audio)
        except sr.WaitTimeoutError:
            return "! I didn't hear anything."
        except sr.UnknownValueError:
            return "! Sorry, I couldn't understand that."
        except sr.RequestError:
            return "! Speech service needs internet."
        except Exception as e:
            return f"! Microphone error: {e}"

    @staticmethod
    def missing_packages():
        missing = []
        if not _TTS:
            missing.append("pyttsx3 (voice output)")
        if not _STT:
            missing.append("SpeechRecognition + PyAudio (mic input)")
        return missing
