"""ALISA JARVIS-style dashboard: orb, tools, live stats, chat, controls."""

import datetime
import math
import random
import threading
import time
import tkinter as tk
from tkinter import messagebox
import urllib.request

from . import config as cfg
from . import license as lic
from . import fbauth
from .ai_client import GeminiClient, DEFAULT_OR_KEY
from .updater import APP_VERSION, check_update, check_announcement
from .brain import handle_command
from .hero import draw_hero
from .memory import load_facts
from .systemctl import SystemControl
from .voice import Voice

# ── gold-on-black JARVIS theme ──
BG = "#05070f"
PANEL = "#0a0f1e"
PANEL2 = "#0d1428"
GOLD = "#eab308"
GOLD_DIM = "#92600a"
TEXT = "#f5f0dc"
MUTED = "#7a7460"
GREEN = "#22c55e"
RED = "#ef4444"
CYAN = "#22d3ee"

TOOLS = [
    ("💬", "Chat", None),
    ("👁", "Vision See", "see"),
    ("🔬", "Deep Research", "deep research "),
    ("🖥", "System Info", "system info"),
    ("🔊", "Volume", "volume "),
    ("📁", "Find File", "find file "),
    ("🌍", "Website", "website "),
    ("📝", "Note", "note "),
    ("👥", "Contacts", "contacts"),
    ("⏰", "Reminder", "remind me in "),
    ("🧠", "Memory", "what do you remember"),
    ("⚙", "Settings", "@settings"),
]


def fetch_weather():
    try:
        req = urllib.request.Request(
            "https://wttr.in/Dhaka?format=%t+%C",
            headers={"User-Agent": "ALISA"},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.read().decode("utf-8", "replace").strip()[:24] or "—"
    except Exception:
        return "—"


def read_stats():
    stats = {"cpu": "—", "ram": "—", "battery": "—"}
    try:
        import psutil
        stats["cpu"] = f"{int(psutil.cpu_percent(interval=1))}%"
        stats["ram"] = f"{int(psutil.virtual_memory().percent)}%"
        try:
            batt = psutil.sensors_battery()
            stats["battery"] = f"{int(batt.percent)}%" if batt else "—"
        except Exception:
            pass
    except ImportError:
        pass
    return stats


class AlisaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ALISA — AI Assistant")
        self.geometry("1180x700")
        self.minsize(960, 600)
        self.configure(bg=BG)

        self.system = SystemControl()
        self.voice = Voice()
        saved = cfg.load()
        self.ai = GeminiClient(saved.get("gemini_key", ""), saved.get("openrouter_key", ""))
        self.history = []
        self.status_mode = "STANDBY"
        self.voice_female = True
        self.camera_on = False
        self._mouth_flag = False
        self.weather = "…"
        self.stats = {"cpu": "…", "ram": "…", "battery": "…"}
        try:
            self.voice.set_gender(True)
        except Exception:
            pass

        self._build()
        self._tick_clock()
        self._animate_orb()
        threading.Thread(target=self._stats_worker, daemon=True).start()
        threading.Thread(target=self._license_recheck, daemon=True).start()
        threading.Thread(target=self._update_check, daemon=True).start()
        self.session = None
        self.login_ok = False
        if self._ensure_login():
            self.login_ok = True
        else:
            try:
                self.destroy()
            except Exception:
                pass
            return
        self._say("Systems online. I'm ALISA — ask me anything, or pick a tool on the left.", speak=False)

    # ── login gate ──
    def _ensure_login(self):
        saved = cfg.load().get("auth")
        sess = fbauth.valid_session(saved) if saved else None
        if not sess and saved:
            sess = fbauth.refresh(dict(saved))
            if sess:
                d = cfg.load()
                d["auth"] = sess
                cfg.save(d)
        if sess:
            self.session = sess
            threading.Thread(target=self._presence_login, daemon=True).start()
            return True
        return self._login_dialog()

    def _presence_login(self):
        try:
            fbauth.write_user_record(self.session, {"plan": "premium" if lic.is_premium() else "free"})
        except Exception:
            pass

    def _login_dialog(self):
        """Professional login/register dialog — blocks until login succeeds or user exits."""
        win = tk.Toplevel(self)
        win.title("ALISA — Login")
        win.geometry("520x540")
        win.minsize(480, 520)
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()
        win.focus_set()
        win.lift()
        try:
            win.attributes("-topmost", True)
            win.after(500, lambda: win.attributes("-topmost", False))
        except Exception:
            pass
        try:
            win.update_idletasks()
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            ww, wh = 520, 540
            win.geometry(f"{ww}x{wh}+{(sw - ww)//2}+{(sh - wh)//2}")
        except Exception:
            pass

        outer = tk.Frame(win, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=16)

        head = tk.Frame(outer, bg=BG)
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text="💜 ALISA", bg=BG, fg=GOLD,
                 font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(head, text="  Your AI Desktop Assistant  •  © Swampod Sarkar",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", pady=(6, 0))

        card = tk.Frame(outer, bg=PANEL2, padx=28, pady=22)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="Welcome back 👋", bg=PANEL2, fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(card, text="Login to enter ALISA. New here? Register — it's free!",
                 bg=PANEL2, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 12))

        mode = {"tab": "login"}
        tab_row = tk.Frame(card, bg=PANEL2)
        tab_row.pack(fill="x", pady=(0, 10))
        login_tab = tk.Button(tab_row, text="Login", relief="flat",
                              font=("Segoe UI", 10, "bold"), padx=18, pady=7)
        reg_tab = tk.Button(tab_row, text="Register", relief="flat",
                            font=("Segoe UI", 10, "bold"), padx=18, pady=7)
        login_tab.pack(side="left", padx=(0, 6))
        reg_tab.pack(side="left")
        submit = tk.Button(card, text="Login ➤", relief="flat",
                           font=("Segoe UI", 12, "bold"), padx=20, pady=9)

        def _paint_tabs():
            active, idle = ("#eab308", "black"), ("#1c2547", MUTED)
            login_tab.configure(bg=active[0] if mode["tab"] == "login" else idle[0],
                                fg=active[1] if mode["tab"] == "login" else idle[1],
                                activebackground="#ca8a04")
            reg_tab.configure(bg=active[0] if mode["tab"] == "register" else idle[0],
                              fg=active[1] if mode["tab"] == "register" else idle[1],
                              activebackground="#1e40af")
            submit.configure(text="Login ➤" if mode["tab"] == "login" else "Create account ✨",
                             bg="#eab308" if mode["tab"] == "login" else "#1e3a8a",
                             fg="black" if mode["tab"] == "login" else "white")

        login_tab.configure(command=lambda: (mode.update(tab="login"), _paint_tabs()))
        reg_tab.configure(command=lambda: (mode.update(tab="register"), _paint_tabs()))
        _paint_tabs()

        tk.Label(card, text="Username", bg=PANEL2, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 2))
        u_entry = tk.Entry(card, font=("Segoe UI", 12), bg="#070b16", fg=TEXT,
                           insertbackground=GOLD, relief="flat")
        u_entry.pack(fill="x", ipady=8)
        u_entry.focus_set()
        tk.Label(card, text="Password (6+ characters)", bg=PANEL2, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 2))
        pw_row = tk.Frame(card, bg=PANEL2)
        pw_row.pack(fill="x")
        p_entry = tk.Entry(pw_row, font=("Segoe UI", 12), bg="#070b16", fg=TEXT,
                           insertbackground=GOLD, relief="flat", show="•")
        p_entry.pack(side="left", fill="x", expand=True, ipady=8)
        eye = tk.Button(pw_row, text="👁", bg="#070b16", fg=MUTED, relief="flat",
                        font=("Segoe UI", 11), padx=10,
                        command=lambda: p_entry.configure(
                            show="" if p_entry.cget("show") == "•" else "•"))
        eye.pack(side="left", padx=(6, 0), ipady=5)
        msg = tk.Label(card, text="", bg=PANEL2, fg=RED, font=("Segoe UI", 9, "bold"),
                       wraplength=360, justify="center")
        msg.pack(pady=(10, 0))
        submit.pack(fill="x", pady=(12, 0))
        p_entry.bind("<Return>", lambda _e: _submit())
        u_entry.bind("<Return>", lambda _e: p_entry.focus_set())
        tk.Button(card, text="✕ Exit", bg=PANEL2, fg=MUTED, relief="flat",
                  font=("Segoe UI", 9), command=lambda: (result.update(ok=False), win.destroy())).pack(pady=(8, 0))
        result = {}
        attempt = {"n": 0}

        def _busy(text):
            msg.configure(text=text, fg=GOLD)
            submit.configure(state="disabled")
            win.update_idletasks()

        def _idle():
            submit.configure(state="normal")

        def _finish(sess, err):
            _idle()
            if sess:
                d = cfg.load()
                d["auth"] = sess
                cfg.save(d)
                self.session = sess
                threading.Thread(target=self._presence_login, daemon=True).start()
                result["ok"] = True
                win.destroy()
            else:
                msg.configure(text="❌ " + (err or "Failed."), fg=RED)

        def _submit():
            u, p = u_entry.get().strip(), p_entry.get()
            if not u or len(p) < 6:
                msg.configure(text="Username + 6+ character password needed.", fg=RED)
                return
            attempt["n"] += 1
            if mode["tab"] == "login":
                _busy("⏳ Logging in…")
                fn = fbauth.signin
            else:
                _busy("⏳ Creating account…")
                fn = fbauth.signup

            state = {"done": False, "sess": None, "err": None}
            t0 = time.monotonic()

            def _w():
                try:
                    sess, err = fn(u, p)
                except Exception as e:
                    sess, err = None, str(e)[:150]
                state.update(done=True, sess=sess, err=err)

            def _poll():
                # runs on main thread — never hangs, never needs cross-thread after()
                try:
                    if not win.winfo_exists():
                        return
                except Exception:
                    return
                if state["done"]:
                    _finish(state["sess"], state["err"])
                    return
                if time.monotonic() - t0 > 40:
                    _idle()
                    msg.configure(text="⚠️ Taking too long — check internet & try again.", fg=GOLD)
                    return
                try:
                    win.after(200, _poll)
                except Exception:
                    pass

            threading.Thread(target=_w, daemon=True).start()
            try:
                win.after(200, _poll)
            except Exception:
                pass

        submit.configure(command=_submit)
        win.protocol("WM_DELETE_WINDOW", lambda: (result.update(ok=False), win.destroy()))
        self.wait_window(win)
        try:
            win.grab_release()
        except Exception:
            pass
        return result.get("ok", False)

    def _update_check(self):
        try:
            info = check_update()
            if info:
                self.update_info = info
                if info.get("update"):
                    self.after(0, lambda: self.bell_btn.configure(text="🔔●", fg=RED))
                    self.after(0, self._say,
                               f"📢 Update available: v{info['latest']} is out! Click the 🔔 bell to see what's new.",
                               "sys", False)
        except Exception:
            pass
        try:
            lic.report_presence()
        except Exception:
            pass
        try:
            ann = check_announcement()
            if ann:
                seen = set(cfg.load().get("seen_ann", []))
                if ann["id"] not in seen:
                    seen.add(ann["id"])
                    d = cfg.load()
                    d["seen_ann"] = sorted(seen)[-20:]
                    cfg.save(d)
                    self.after(0, lambda: self._announce_dialog(ann))
        except Exception:
            pass

    def _announce_dialog(self, ann):
        win = tk.Toplevel(self)
        win.title("📢 Notice")
        win.geometry("420x300")
        win.configure(bg=BG)
        win.transient(self)
        tk.Label(win, text="📢 " + ann["title"], bg=BG, fg=GOLD,
                 font=("Segoe UI", 14, "bold"), wraplength=380,
                 justify="center").pack(pady=(16, 8))
        box = tk.Text(win, bg=PANEL2, fg=TEXT, font=("Segoe UI", 10), wrap="word",
                      height=8, relief="flat", padx=10, pady=8)
        box.pack(fill="both", expand=True, padx=20)
        box.insert("end", ann["body"])
        box.configure(state="disabled")
        tk.Button(win, text="Got it ✓", bg=GOLD, fg="black", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=24, pady=7,
                  activebackground="#ca8a04", command=win.destroy).pack(pady=12)

    def _updates_dialog(self):
        info = self.update_info
        win = tk.Toplevel(self)
        win.title("ALISA Updates")
        win.geometry("440x380")
        win.configure(bg=BG)
        win.transient(self)
        tk.Label(win, text="🔔 Update Channel", bg=BG, fg=GOLD,
                 font=("Segoe UI", 16, "bold")).pack(pady=(16, 4))
        tk.Label(win, text=f"Your version: v{APP_VERSION}", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack()
        if not info:
            tk.Label(win, text="Couldn't reach the update server.\nCheck your internet and try again.",
                     bg=BG, fg=TEXT, font=("Segoe UI", 10), wraplength=380,
                     justify="center").pack(pady=12)
        elif not info.get("update"):
            tk.Label(win, text=f"✅ You're on the latest version (v{info.get('latest', APP_VERSION)})!",
                     bg=BG, fg=GREEN, font=("Segoe UI", 11, "bold"), wraplength=380,
                     justify="center").pack(pady=12)
        else:
            tk.Label(win, text=f"🎉 v{info['latest']} is available!",
                     bg=BG, fg=GREEN, font=("Segoe UI", 13, "bold")).pack(pady=(8, 2))
            tk.Label(win, text="What's new:", bg=BG, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20)
            box = tk.Text(win, bg=PANEL2, fg=TEXT, font=("Segoe UI", 10), wrap="word",
                          height=8, relief="flat", padx=10, pady=8)
            box.pack(fill="both", expand=True, padx=20, pady=(4, 8))
            box.insert("end", info.get("notes", ""))
            box.configure(state="disabled")
            tk.Button(win, text="⬇ Download Update", bg=GOLD, fg="black", relief="flat",
                      font=("Segoe UI", 11, "bold"), padx=24, pady=8,
                      activebackground="#ca8a04",
                      command=lambda: __import__("webbrowser").open(info["url"])).pack(pady=(0, 14))

    def _license_recheck(self):
        try:
            result = lic.recheck_saved_key()
            if result == "revoked":
                self.after(0, self._refresh_status)
                self.after(0, self._say,
                           "⚠️ This license key was revoked by the owner. Back to FREE plan.", "sys", False)
            elif result == "bound":
                self.after(0, self._refresh_status)
                self.after(0, self._say,
                           "⚠️ This key is bound to another device. Back to FREE plan.", "sys", False)
        except Exception:
            pass

    # ══ layout ══
    def _panel_label(self, parent, text):
        lbl = tk.Label(parent, text=text, bg=PANEL, fg=MUTED, font=("Consolas", 9, "bold"))
        lbl.pack(fill="x", padx=10, pady=(8, 2))
        return lbl

    def _build(self):
        # ── top status strip ──
        top = tk.Frame(self, bg=BG, height=34)
        top.pack(fill="x", padx=10, pady=(8, 0))
        self.mode_var = tk.StringVar(value="● STANDBY")
        tk.Label(top, textvariable=self.mode_var, bg=BG, fg=GREEN,
                 font=("Consolas", 10, "bold")).pack(side="left")
        pills = tk.Frame(top, bg=BG)
        pills.pack(side="right")
        tk.Button(pills, text="🎤 MIC", bg="#0f2a1a", fg=GREEN, relief="flat",
                  font=("Consolas", 9, "bold"), padx=10, pady=3,
                  activebackground="#14532d", activeforeground="white",
                  command=self._mic).pack(side="left", padx=3)
        self.api_pill = tk.Button(pills, text="🔑 API", bg="#2a1f0f", fg=GOLD, relief="flat",
                                  font=("Consolas", 9, "bold"), padx=10, pady=3,
                                  activebackground="#451a03", activeforeground="white",
                                  command=self._settings)
        self.api_pill.pack(side="left", padx=3)
        self.plan_pill = tk.Button(pills, text="🎫 FREE", bg="#1c2547", fg=MUTED, relief="flat",
                                   font=("Consolas", 9, "bold"), padx=10, pady=3,
                                   activebackground="#2a3563", activeforeground="white",
                                   command=self._activation)
        self.plan_pill.pack(side="left", padx=3)
        self.update_info = None
        self.bell_btn = tk.Button(pills, text="🔔", bg="#1c2547", fg=MUTED, relief="flat",
                                  font=("Consolas", 9, "bold"), padx=10, pady=3,
                                  activebackground="#2a3563", activeforeground="white",
                                  command=self._updates_dialog)
        self.bell_btn.pack(side="left", padx=3)
        tk.Button(pills, text="💜 ALISA MODE", bg="#2a1030", fg="#e879f9", relief="flat",
                  font=("Consolas", 9, "bold"), padx=10, pady=3,
                  activebackground="#4a044e", activeforeground="white",
                  command=lambda: self._say("ALISA mode engaged. All systems nominal.", speak=False)).pack(side="left", padx=3)
        self._refresh_api_pill()

        # ── main split ──
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=8)

        # left: tools
        left = tk.Frame(main, bg=PANEL, width=190)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        tk.Label(left, text="⚙ All Tools", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 13, "bold"), pady=10).pack(fill="x")
        for icon, label, cmd in TOOLS:
            b = tk.Button(left, text=f"  {icon}  {label}", anchor="w", bg=PANEL, fg=TEXT,
                          relief="flat", font=("Segoe UI", 10), pady=7,
                          activebackground="#1c2547", activeforeground=GOLD,
                          command=lambda c=cmd: self._tool(cmd=c))
            b.pack(fill="x", padx=6, pady=1)

        # center: orb + controls
        center = tk.Frame(main, bg=BG)
        center.pack(side="left", fill="both", expand=True)
        self.orb = tk.Canvas(center, bg=BG, highlightthickness=0)
        self.orb.pack(fill="both", expand=True)
        self._orb_t = 0
        self._blink = 3.0
        self.emotion = "neutral"
        # voice waveform strip
        self.wave = tk.Canvas(center, bg=BG, height=34, highlightthickness=0)
        self.wave.pack(fill="x", padx=20)
        self._stars = [(random.random(), random.random(), random.uniform(0.5, 2.2))
                       for _ in range(60)]

        controls = tk.Frame(center, bg=BG, pady=10)
        controls.pack(fill="x")
        crow = tk.Frame(controls, bg=BG)
        crow.pack()
        self.mute_btn = tk.Button(crow, text="🔇 Mute", bg="#7f1d1d", fg="white", relief="flat",
                                  font=("Segoe UI", 10, "bold"), padx=22, pady=9,
                                  activebackground="#991b1b", command=self._toggle_voice)
        self.mute_btn.pack(side="left", padx=6)
        tk.Button(crow, text="🖥 Share Screen", bg="#134e4a", fg=CYAN, relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=18, pady=9,
                  activebackground="#0f766e", command=lambda: self.send("read screen")).pack(side="left", padx=6)
        tk.Button(crow, text="🎤 Speak", bg="#1e3a8a", fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=26, pady=9,
                  activebackground="#1e40af", command=self._mic).pack(side="left", padx=6)
        crow2 = tk.Frame(controls, bg=BG)
        crow2.pack(pady=(8, 0))
        self.cam_btn = tk.Button(crow2, text="📷 Camera Off", bg=PANEL2, fg=MUTED, relief="flat",
                                 font=("Segoe UI", 9, "bold"), padx=16, pady=7, command=self._toggle_cam)
        self.cam_btn.pack(side="left", padx=6)
        self.vgender_btn = tk.Button(crow2, text="Voice: Female", bg="#3b0764", fg="#e879f9", relief="flat",
                                     font=("Segoe UI", 9, "bold"), padx=16, pady=7, command=self._toggle_gender)
        self.vgender_btn.pack(side="left", padx=6)

        # right: stats + chat
        right = tk.Frame(main, bg=PANEL, width=320)
        right.pack(side="left", fill="y", padx=(8, 0))
        right.pack_propagate(False)

        self._panel_label(right, "System Monitor")
        self.stat_vars = {}
        for key, icon, label in (("weather", "☁", "Weather"), ("battery", "🔋", "Battery"),
                                 ("cpu", "🔵", "CPU"), ("ram", "🟠", "RAM"), ("time", "⏰", "Time")):
            row = tk.Frame(right, bg=PANEL)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=f"{icon} {label}", bg=PANEL, fg=MUTED,
                     font=("Consolas", 10, "bold")).pack(side="left")
            var = tk.StringVar(value="…")
            tk.Label(row, textvariable=var, bg=PANEL, fg=TEXT,
                     font=("Consolas", 11, "bold")).pack(side="right")
            self.stat_vars[key] = var

        tabs = tk.Frame(right, bg=PANEL)
        tabs.pack(fill="x", padx=10, pady=(10, 0))
        tk.Button(tabs, text="💬 Chat", bg=PANEL2, fg=CYAN, relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=12, pady=6).pack(side="left", fill="x", expand=True)
        tk.Button(tabs, text="👁 Vision", bg=PANEL, fg=MUTED, relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=12, pady=6,
                  command=lambda: self.send("see")).pack(side="left", fill="x", expand=True)

        self.chat = tk.Text(right, bg="#070b16", fg=TEXT, font=("Segoe UI", 10), wrap="word",
                            state="disabled", padx=10, pady=8, relief="flat", height=14,
                            insertbackground=TEXT)
        self.chat.pack(fill="both", expand=True, padx=10, pady=6)
        self.chat.tag_config("me", foreground=CYAN)
        self.chat.tag_config("alisa", foreground=TEXT)
        self.chat.tag_config("sys", foreground=MUTED)

        entry_row = tk.Frame(right, bg=PANEL)
        entry_row.pack(fill="x", padx=10, pady=(0, 10))
        self.entry = tk.Entry(entry_row, bg="#070b16", fg=TEXT, font=("Segoe UI", 10),
                              relief="flat", insertbackground=GOLD)
        self.entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 6))
        self.entry.bind("<Return>", lambda _e: self.send())
        tk.Button(entry_row, text="➤", bg=GOLD, fg="black", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=12,
                  activebackground="#ca8a04", command=self.send).pack(side="left")

        # bottom status bar
        self.status = tk.Label(self, text="", bg=BG, fg=MUTED, font=("Consolas", 9),
                               anchor="w", padx=14, pady=4)
        self.status.pack(fill="x")
        self._refresh_status()

    # ══ orb animation ══
    def _mouth_open(self):
        """True lip sync: flag driven by actual word audio callbacks."""
        return self.status_mode == "SPEAKING" and bool(self._mouth_flag)

    def _animate_orb(self):
        try:
            c = self.orb
            w, h = c.winfo_width(), c.winfo_height()
            if w > 50 and h > 50:
                c.delete("all")
                cx, cy = w / 2, h / 2
                s = max(0.5, min(w, h) / 430)
                # stars
                for sx, sy, r in self._stars:
                    c.create_oval(sx * w, sy * h, sx * w + r, sy * h + r,
                                  fill="#3a3f5e", outline="")
                t = self._orb_t
                # blink timer
                self._blink -= 0.08
                if self._blink <= 0:
                    self._blink = 2.4 + random.random() * 2.6
                blink = self._blink < 0.18
                bob = math.sin(t * 1.2) * 4 * s
                speaking = self._mouth_open()
                draw_hero(c, cx, cy + bob, s, blink, speaking, self.emotion)
                c.create_text(cx, cy - 168 * s, text="ALISA", fill=GOLD,
                              font=("Segoe UI", int(30 * s), "bold"))
                c.create_text(cx, h - 22, text=self.status_mode, fill=MUTED,
                              font=("Consolas", 11, "bold"))
                # voice waveform
                try:
                    wv = self.wave
                    ww, wh = wv.winfo_width(), 34
                    if ww > 60:
                        wv.delete("all")
                        live = self.status_mode in ("SPEAKING", "LISTENING")
                        n, gap = 28, 0
                        bw = ww / n
                        for i in range(n):
                            if live:
                                bh = 4 + abs(math.sin(t * 4 + i * 0.7)) * (wh - 8)
                            else:
                                bh = 3
                            x0 = i * bw + 2
                            col = "#22d3ee" if self.status_mode == "SPEAKING" else (
                                GOLD if live else "#2a3352")
                            wv.create_rectangle(x0, (wh - bh) / 2, x0 + bw - 4, (wh + bh) / 2,
                                                fill=col, outline="")
                except Exception:
                    pass
            self._orb_t += 0.08
        except Exception:
            pass
        self.after(80, self._animate_orb)

    # ══ clock / stats ══
    def _tick_clock(self):
        try:
            self.stat_vars["time"].set(datetime.datetime.now().strftime("%I:%M %p"))
        except Exception:
            pass
        self.after(1000, self._tick_clock)

    def _stats_worker(self):
        self.weather = fetch_weather()
        try:
            self.after(0, lambda: self.stat_vars["weather"].set(self.weather))
        except Exception:
            pass
        while True:
            try:
                self.stats = read_stats()
                w, s = self.weather, self.stats
                self.after(0, lambda: self._apply_stats(w, s))
            except Exception:
                pass
            threading.Event().wait(8)

    def _apply_stats(self, weather, stats):
        try:
            self.stat_vars["weather"].set(weather)
            self.stat_vars["battery"].set(stats["battery"])
            self.stat_vars["cpu"].set(stats["cpu"])
            self.stat_vars["ram"].set(stats["ram"])
        except Exception:
            pass

    # ══ chat plumbing (same brain as before) ══
    def _set_mode(self, mode, color=None):
        self.status_mode = mode
        colors = {"STANDBY": GREEN, "LISTENING": GOLD, "THINKING": GOLD, "SPEAKING": CYAN}
        self.mode_var.set(f"● {mode}")
        try:
            top = self.winfo_children()[0]
            top.winfo_children()[0].configure(fg=color or colors.get(mode, GREEN))
        except Exception:
            pass

    @staticmethod
    def _emotion_for(text):
        t = (text or "").lower()
        if any(k in t for k in ("failed", "could not", "missing", "empty", "error", "sorry", "unable", "off (")):
            return "sad"
        if any(k in t for k in ("researching", "looking", "listening", "one moment", "working")):
            return "thinking"
        if any(k in t for k in ("good morning", "good afternoon", "good evening", "আসসালামু",
                                "joke", "haha", "congrat", "awesome", "great", "welcome", "🎉", "😄")):
            return "happy"
        if "?" in t and len(t) < 120:
            return "surprised"
        return "neutral"

    def _say(self, text, who="alisa", speak=True, emotion=None):
        if who == "alisa":
            self.emotion = emotion or self._emotion_for(text)
        self.chat.configure(state="normal")
        prefix = {"me": "◆ You: ", "alisa": "⬢ ALISA: ", "sys": "… "}[who]
        self.chat.insert("end", prefix + text + "\n\n", who)
        self.chat.configure(state="disabled")
        self.chat.see("end")
        if speak and who == "alisa":
            self._set_mode("SPEAKING")
            threading.Thread(target=self._speak_done, args=(text,), daemon=True).start()

    def _speak_done(self, text):
        def _tick(open_):
            self._mouth_flag = bool(open_)
        try:
            self.voice.speak_sync(text, tick=_tick)
        finally:
            self._mouth_flag = False
            try:
                self.after(0, lambda: self._set_mode("STANDBY"))
            except Exception:
                pass

    def send(self, text=None):
        text = self.entry.get().strip() if text is None else text
        if not text:
            return
        try:
            self.entry.delete(0, "end")
        except Exception:
            pass
        self.emotion = "thinking"
        self._say(text, who="me", speak=False)
        self._set_mode("THINKING")
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    def _process(self, text):
        try:
            reply, use_ai = handle_command(text, self.system)
        except Exception as e:
            reply, use_ai = f"Command error: {e}", False
        if reply.startswith("@@RESEARCH:"):
            self._do_research(reply[len("@@RESEARCH:"):])
            return
        if reply.startswith("@@ANALYZE:"):
            self._do_analyze(reply[len("@@ANALYZE:"):])
            return
        if reply.startswith("@@VISION:"):
            self._do_vision(reply[len("@@VISION:"):])
            return
        if "@@AI:" in reply:
            done, _, ai_part = reply.partition("@@AI:")
            if done.strip():
                self.after(0, self._say, done.strip())
            self._ai_answer(ai_part.strip())
            return
        if use_ai:
            self._ai_answer(text)
        else:
            self.after(0, self._say, reply)
            self.after(0, lambda: self._set_mode("STANDBY"))

    def _ai_answer(self, text):
        if not self.ai.ready:
            reply = "For open questions I need a free AI key — open Settings and paste your Gemini (or OpenRouter) key."
        else:
            try:
                reply = self.ai.ask(text, self.history, load_facts())
                self.history += [{"role": "user", "parts": [text]}, {"role": "model", "parts": [reply]}]
                self.history = self.history[-10:]
            except Exception as e:
                reply = f"AI error: {e}"
        self.after(0, self._say, reply)
        self.after(0, self._refresh_status)

    def _do_research(self, topic):
        self.after(0, self._say, f"Researching '{topic}' — this takes ~20 seconds…", "sys", False)
        threading.Thread(target=self._research_worker, args=(topic,), daemon=True).start()

    def _research_worker(self, topic):
        try:
            report = self.ai.ask(
                f"Write a detailed research report on: {topic}\n"
                "Structure: Overview, Key points (bullets), Important facts/numbers, Conclusion. ~300 words.",
                facts=load_facts(),
            )
            import datetime as _dt
            import os as _os
            safe = "".join(c for c in topic[:30] if c.isalnum() or c in " -").strip() or "topic"
            path = _os.path.join(_os.path.expanduser("~"), "Desktop", f"alisa-research-{safe}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"ALISA Deep Research: {topic}\n{'=' * 40}\n\n{report}\n")
            self.after(0, self._say, f"Research done and saved to Desktop!\n\n{report[:600]}")
        except Exception as e:
            self.after(0, self._say, f"Research failed: {e}")
        finally:
            self.after(0, lambda: self._set_mode("STANDBY"))

    def _do_analyze(self, screen_text):
        self.after(0, self._say, "Analyzing your screen…", "sys", False)
        threading.Thread(target=self._analyze_worker, args=(screen_text,), daemon=True).start()

    def _analyze_worker(self, screen_text):
        try:
            summary = self.ai.ask(
                "Here is text captured from my screen. Summarize what I'm looking at and "
                "point out anything important (errors, messages, tasks). Keep it under 80 words:\n\n"
                + screen_text,
                facts=load_facts(),
            )
            self.after(0, self._say, f"🖥 {summary}")
        except Exception as e:
            self.after(0, self._say, f"Analysis failed: {e}")
        finally:
            self.after(0, lambda: self._set_mode("STANDBY"))

    def _do_vision(self, path):
        self.after(0, self._say, "Looking at the camera…", "sys", False)
        threading.Thread(target=self._vision_worker, args=(path,), daemon=True).start()

    def _vision_worker(self, path):
        try:
            import os
            with open(path, "rb") as f:
                data = f.read()
            os.remove(path)
            desc = self.ai.describe_image(data, "Describe what you see in one short paragraph.")
            self.after(0, self._say, f"👁 {desc}")
        except Exception as e:
            self.after(0, self._say, f"Vision failed: {e}")
        finally:
            self.after(0, lambda: self._set_mode("STANDBY"))

    # ══ controls ══
    def _tool(self, cmd=None):
        if cmd == "@settings":
            self._settings()
            return
        if not cmd:
            return
        # complete commands run at once, partial ones fill the entry
        if not cmd.endswith(" "):
            self.send(cmd)
            return
        try:
            self.entry.delete(0, "end")
            self.entry.insert(0, cmd)
            self.entry.focus_set()
        except Exception:
            pass

    def _mic(self):
        self._set_mode("LISTENING")
        self._say("Listening… speak now!", who="sys", speak=False)
        threading.Thread(target=self._mic_worker, daemon=True).start()

    def _mic_worker(self):
        heard = self.voice.listen()
        self.after(0, lambda: self._set_mode("THINKING"))
        if heard.startswith("!"):
            self.after(0, self._say, heard[2:], "sys", False)
            self.after(0, lambda: self._set_mode("STANDBY"))
        else:
            self.after(0, self.send, heard)

    def _toggle_voice(self):
        self.voice.enabled = not self.voice.enabled
        self.mute_btn.configure(text="🔇 Mute" if self.voice.enabled else "🔈 Unmute")
        self._refresh_status()

    def _toggle_cam(self):
        self.camera_on = not self.camera_on
        self.cam_btn.configure(text="📷 Camera On" if self.camera_on else "📷 Camera Off")

    def _toggle_gender(self):
        self.voice_female = not self.voice_female
        ok = self.voice.set_gender(self.voice_female)
        self.vgender_btn.configure(text=f"Voice: {'Female' if self.voice_female else 'Male'}")
        self._say(f"Voice set to {'female' if self.voice_female else 'male'}.", speak=False)
        if ok:
            self._say("This is how I sound now.", speak=True)

    def _refresh_status(self):
        ai_state = f"AI: {self.ai.provider}" if self.ai.ready else "AI: off"
        voice_state = "Voice: on" if self.voice.enabled else "Voice: muted"
        plan = "💎 PREMIUM" if lic.is_premium() else "FREE"
        try:
            self.status.configure(text=f"{ai_state}  ·  {voice_state}  ·  {plan}  ·  Camera: {'on' if self.camera_on else 'off'}")
            self._refresh_api_pill()
            self.plan_pill.configure(
                text="💎 PREMIUM" if lic.is_premium() else "🎫 FREE",
                fg="#fbbf24" if lic.is_premium() else MUTED,
            )
        except Exception:
            pass

    def _refresh_api_pill(self):
        try:
            self.api_pill.configure(text="🔑 API ✓" if self.ai.ready else "🔑 API")
        except Exception:
            pass

    def _activation(self):
        win = tk.Toplevel(self)
        win.title("ALISA Activation Center")
        win.geometry("440x340")
        win.configure(bg=BG)
        win.transient(self)
        tk.Label(win, text="🎫 Activation Center", bg=BG, fg=GOLD,
                 font=("Segoe UI", 16, "bold")).pack(pady=(16, 4))
        tk.Label(win, text="💎 PREMIUM — ৳150 lifetime", bg=BG, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack()
        tk.Label(win, text="Vision + Deep Research + Website Generator, forever.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(pady=(0, 4))
        buy_btn = tk.Button(win, text="💬 Buy on Telegram: @swampod", bg="#229ED9", fg="white",
                            relief="flat", font=("Segoe UI", 10, "bold"), padx=16, pady=7,
                            activebackground="#1b8ac0",
                            command=lambda: __import__("webbrowser").open("https://t.me/swampod"))
        buy_btn.pack(pady=(6, 0))
        status = "💎 PREMIUM — all features unlocked!" if lic.is_premium() else "FREE plan — Vision, Research & Website Generator are locked."
        tk.Label(win, text=status, bg=BG, fg=TEXT, font=("Segoe UI", 10),
                 wraplength=380, justify="center").pack(padx=16)
        tk.Label(win, text="Get a key from the owner (bKash ৳150), then paste below:", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(pady=(12, 2))
        k_entry = tk.Entry(win, font=("Consolas", 11), width=40, justify="center")
        k_entry.pack(padx=16, ipady=6)
        msg = tk.Label(win, text="", bg=BG, fg=RED, font=("Segoe UI", 9, "bold"))
        msg.pack(pady=(6, 0))

        def _activate():
            key = k_entry.get()
            if not lic.verify_key(key):
                msg.configure(text="❌ Invalid key format.", fg=RED)
                return
            msg.configure(text="⏳ Checking online…", fg=GOLD)
            win.update_idletasks()

            def _worker():
                result = lic.verify_online(key)
                if result is False:
                    self.after(0, lambda: msg.configure(text="❌ Key not found / revoked.", fg=RED))
                    return
                if result == "bound":
                    self.after(0, lambda: msg.configure(
                        text="⚠️ Key already used on another device.\nContact @swampod to reset.", fg=GOLD))
                    return
                if result is None:
                    self.after(0, lambda: msg.configure(
                        text="⚠️ No internet — connect once to activate.", fg=GOLD))
                    return
                lic.save_license(key.strip().upper())
                self.after(0, self._refresh_status)
                self.after(0, lambda: msg.configure(text="✅ Activated! Welcome to PREMIUM!", fg=GREEN))
                self.after(1200, win.destroy)

            import threading as _th
            _th.Thread(target=_worker, daemon=True).start()

        tk.Button(win, text="Activate ✨", bg=GOLD, fg="black", relief="flat",
                  font=("Segoe UI", 11, "bold"), padx=30, pady=8,
                  activebackground="#ca8a04", command=_activate).pack(pady=12)

    def _settings(self):
        win = tk.Toplevel(self)
        win.title("ALISA Settings")
        win.geometry("440x300")
        win.configure(bg=BG)
        win.transient(self)
        saved = cfg.load()
        # show the effective (default) key so the user sees it's saved
        if not saved.get("openrouter_key"):
            saved = {**saved, "openrouter_key": DEFAULT_OR_KEY}
        tk.Label(win, text="Gemini API key (free, optional upgrade):", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        g_entry = tk.Entry(win, font=("Segoe UI", 10), width=48, show="•")
        g_entry.pack(padx=16)
        g_entry.insert(0, saved.get("gemini_key", ""))
        tk.Label(win, text="OpenRouter key (free fallback, optional):", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(10, 2))
        o_entry = tk.Entry(win, font=("Segoe UI", 10), width=48, show="•")
        o_entry.pack(padx=16)
        o_entry.insert(0, saved.get("openrouter_key", ""))
        tk.Label(win, text="Keys: aistudio.google.com · openrouter.ai/keys", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(padx=16, pady=(8, 0))

        def _save():
            d = cfg.load()
            d["gemini_key"] = g_entry.get().strip()
            d["openrouter_key"] = o_entry.get().strip()
            cfg.save(d)
            s = cfg.load()
            self.ai = GeminiClient(s.get("gemini_key", ""), s.get("openrouter_key", ""))
            self._refresh_status()
            messagebox.showinfo("ALISA", "Saved! AI: " + self.ai.provider if self.ai.ready else "Saved! AI still off (no key).")
            win.destroy()

        def _logout():
            d = cfg.load()
            d.pop("auth", None)
            cfg.save(d)
            self.session = None
            messagebox.showinfo("ALISA", "Logged out! Restart the app to login again.")
            win.destroy()

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(pady=12)
        tk.Button(btn_row, text="Save", bg=GOLD, fg="black", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=20, pady=6, command=_save).pack(side="left", padx=5)
        tk.Button(btn_row, text="Logout", bg="#7f1d1d", fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=20, pady=6, command=_logout).pack(side="left", padx=5)


def main():
    import sys as _sys
    import threading as _th
    import traceback as _tb
    def _log(exc, val, tb):
        try:
            with open(os.path.join(os.path.expanduser("~"), "Desktop",
                                   "alisa-error.log"), "a", encoding="utf-8") as f:
                f.write("".join(_tb.format_exception(exc, val, tb)))
                f.write("\n" + "=" * 60 + "\n")
        except Exception:
            pass

    _sys.excepthook = lambda e, v, t: _log(e, v, t)
    _th.excepthook = lambda a: _log(a.exc_type, a.exc_value, a.exc_traceback)

    def _tk_report(exc, val, tb):
        _log(exc, val, tb)

    tk.Tk.report_callback_exception = _tk_report
    app = AlisaApp()
    if not getattr(app, "login_ok", False):
        # login failed/cancelled — exit without ever showing the dashboard
        try:
            app.destroy()
        except Exception:
            pass
        return
    app.mainloop()
