"""ALISA system controls (Windows). Optional deps degrade gracefully."""

import ctypes
import csv
import io
import subprocess

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    _PYCAW = True
except Exception:
    _PYCAW = False

try:
    import screen_brightness_control as sbc
    _SBC = True
except Exception:
    _SBC = False

VK_KEYS = {
    "enter": 0x0D, "tab": 0x09, "escape": 0x1B, "esc": 0x1B, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E, "up": 0x26, "down": 0x28,
    "left": 0x25, "right": 0x27, "home": 0x24, "end": 0x23,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
    "f6": 0x75, "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79,
    "f11": 0x7A, "f12": 0x7B,
}


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_void_p)]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_void_p)]


class _UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("u", _UNION)]


def _send(inp):
    n = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    if n != 1:
        raise RuntimeError("SendInput rejected")


def _key_event(vk, up=False):
    inp = _INPUT()
    inp.type = 1
    inp.u.ki = _KEYBDINPUT(vk, 0, 0x0002 if up else 0, 0, None)
    _send(inp)


def _mouse_event(flags, dx=0, dy=0):
    inp = _INPUT()
    inp.type = 0
    inp.u.mi = _MOUSEINPUT(dx, dy, 0, flags, 0, None)
    _send(inp)


def _endpoint():
    dev = AudioUtilities.GetSpeakers()
    if hasattr(dev, "EndpointVolume"):  # pycaw >= 2024 API
        return dev.EndpointVolume
    # legacy pycaw API
    interface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


class SystemControl:
    name = "system"

    def volume_delta(self, delta):
        if not _PYCAW:
            return ("Volume control needs 'pip install pycaw comtypes'.", False)
        try:
            ep = _endpoint()
            level = max(0.0, min(1.0, ep.GetMasterVolumeLevelScalar() + delta / 100.0))
            ep.SetMasterVolumeLevelScalar(level, None)
            return (f"Volume set to {int(level * 100)}%.", False)
        except Exception as e:
            return (f"Volume failed: {e}", False)

    def set_mute(self, mute):
        if not _PYCAW:
            return ("Mute needs 'pip install pycaw comtypes'.", False)
        try:
            _endpoint().SetMute(1 if mute else 0, None)
            return ("Muted." if mute else "Unmuted.", False)
        except Exception as e:
            return (f"Mute failed: {e}", False)

    def set_brightness(self, level):
        if not _SBC:
            return ("Brightness needs 'pip install screen-brightness-control'.", False)
        try:
            sbc.set_brightness(level)
            return (f"Brightness set to {level}%.", False)
        except Exception as e:
            return (f"Brightness failed: {e}", False)

    # ── keyboard / mouse (stdlib ctypes, no deps) ──
    @staticmethod
    def _vk(name):
        name = (name or "").lower()
        if len(name) == 1:
            return ctypes.windll.user32.VkKeyScanW(ord(name)) & 0xFF
        return VK_KEYS.get(name)

    def press_key(self, name):
        vk = self._vk(name)
        if not vk:
            return (f"Unknown key '{name}'. Try enter, tab, escape, space, arrows, F1–F12.", False)
        try:
            _key_event(vk, up=False)
            _key_event(vk, up=True)
            return (f"Pressed {name}.", False)
        except Exception as e:
            return (f"Key press failed: {e}", False)

    def type_text(self, text):
        text = (text or "")[:200]
        if not text:
            return ("Tell me what to type.", False)
        try:
            user32 = ctypes.windll.user32
            for ch in text:
                vk_info = user32.VkKeyScanW(ord(ch))
                vk = vk_info & 0xFF
                shift = (vk_info >> 8) & 0xFF
                if shift & 1:
                    _key_event(0x10, up=False)
                _key_event(vk, up=False)
                _key_event(vk, up=True)
                if shift & 1:
                    _key_event(0x10, up=True)
            return (f"Typed {len(text)} character(s).", False)
        except Exception as e:
            return (f"Typing failed: {e}", False)

    def mouse_click(self):
        try:
            _mouse_event(0x0002)
            _mouse_event(0x0004)
            return ("Clicked.", False)
        except Exception as e:
            return (f"Click failed: {e}", False)

    def mouse_move(self, x, y):
        try:
            if not ctypes.windll.user32.SetCursorPos(int(x), int(y)):
                raise RuntimeError("out of screen range")
            return (f"Mouse moved to ({int(x)}, {int(y)}).", False)
        except Exception as e:
            return (f"Mouse move failed: {e}", False)

    def window_show(self, cmd):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            ctypes.windll.user32.ShowWindow(hwnd, 3 if cmd == "max" else 9)
            return (f"Window {'maximized' if cmd == 'max' else 'restored'}.", False)
        except Exception as e:
            return (f"Window command failed: {e}", False)

    @staticmethod
    def list_windows():
        try:
            out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True, timeout=15).stdout
            names = sorted({row[0].replace(".exe", "") for row in csv.reader(io.StringIO(out)) if row})
            gui_apps = [n for n in names if not n.lower().startswith(
                ("svchost", "conhost", "runtimebroker", "sihost", "taskhostw", "dwm",
                 "csrss", "smss", "wininit", "services", "lsass", "fontdrvhost"))]
            return gui_apps[:25]
        except Exception:
            return []

    @staticmethod
    def missing_features():
        missing = []
        if not _PYCAW:
            missing.append("volume (pip install pycaw comtypes)")
        if not _SBC:
            missing.append("brightness (pip install screen-brightness-control)")
        return missing
