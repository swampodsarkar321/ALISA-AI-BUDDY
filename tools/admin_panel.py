"""ALISA Admin Panel — OWNER ONLY. Never ship this to buyers!

Run:  python tools/admin_panel.py
Needs: pip install firebase_admin
Setup: Firebase Console → Project settings → Service accounts →
       Generate new private key → save path in the panel (stored locally).
"""

import datetime
import json
import os
import sys
import time
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

BG = "#0b0f1e"
PANEL = "#111832"
TEXT = "#e8eaf6"
MUTED = "#8b90ad"
GOLD = "#eab308"
GREEN = "#22c55e"
RED = "#ef4444"

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_config.json")


def load_cfg():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cfg(d):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)


def ago(ts):
    try:
        s = int(datetime.datetime.now().timestamp() - float(ts or 0))
    except (TypeError, ValueError):
        return "—"
    if s < 90:
        return "now"
    if s < 3600:
        return f"{s // 60}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ALISA Admin Panel 👑")
        self.geometry("980x640")
        self.minsize(860, 560)
        self.configure(bg=BG)
        self.db = None
        self._build()
        self._try_connect(silent=True)

    # ── setup ──
    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(top, text="👑 ALISA Admin Panel", bg=BG, fg=GOLD,
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        self.conn_var = tk.StringVar(value="● disconnected")
        self.conn_label = tk.Label(top, textvariable=self.conn_var, bg=BG, fg=RED,
                                   font=("Consolas", 10, "bold"))
        self.conn_label.pack(side="right")

        setup = tk.LabelFrame(self, text=" Firebase service account (owner only) ",
                              bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        setup.pack(fill="x", padx=12, pady=8)
        cfg = load_cfg()
        tk.Label(setup, text="Service JSON path:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(side="left", padx=(10, 4))
        self.cred_entry = tk.Entry(setup, font=("Segoe UI", 9), width=60)
        self.cred_entry.pack(side="left", padx=4, pady=8)
        self.cred_entry.insert(0, cfg.get("cred_path", ""))
        tk.Label(setup, text="DB URL:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(side="left", padx=(10, 4))
        self.db_entry = tk.Entry(setup, font=("Segoe UI", 9), width=40)
        self.db_entry.pack(side="left", padx=4)
        self.db_entry.insert(0, cfg.get("db_url", "https://chat-2-me-c3213-default-rtdb.firebaseio.com"))
        tk.Button(setup, text="Connect", bg=GOLD, fg="black", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=14,
                  command=self._connect).pack(side="left", padx=8)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self._tab_dashboard()
        self._tab_keys()
        self._tab_updates()
        self._tab_notify()

    def _db_or_warn(self):
        if self.db is None:
            messagebox.showwarning("Admin", "Connect Firebase first (service JSON above).")
            return None
        return self.db

    def _try_connect(self, silent=False):
        cfg = load_cfg()
        path, url = cfg.get("cred_path", ""), cfg.get("db_url", "")
        if not path or not os.path.isfile(path):
            if not silent:
                messagebox.showwarning("Admin", "Service JSON file not found.")
            return False
        try:
            import firebase_admin
            from firebase_admin import credentials, db as fdb
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(credentials.Certificate(path), {"databaseURL": url})
            self.db = fdb
            save_cfg({"cred_path": path, "db_url": url})
            self.conn_label.configure(fg=GREEN)
            self.conn_var.set("● connected")
            self.refresh_all()
            return True
        except ImportError:
            messagebox.showerror("Admin", "Install first: pip install firebase-admin")
        except Exception as e:
            messagebox.showerror("Admin", f"Connect failed:\n{e}")
        return False

    def _connect(self):
        save_cfg({"cred_path": self.cred_entry.get().strip(),
                  "db_url": self.db_entry.get().strip()})
        self._try_connect()

    # ── dashboard ──
    def _tab_dashboard(self):
        f = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(f, text="  📊 Dashboard  ")
        self.dash_vars = {}
        for i, (label, key) in enumerate([("Total keys", "total"), ("Active devices", "active"),
                                          ("Revoked", "revoked"), ("Free users*", "free")]):
            card = tk.Frame(f, bg="#0d1428", padx=16, pady=12)
            card.grid(row=0, column=i, padx=8, pady=12, sticky="nsew")
            f.grid_columnconfigure(i, weight=1)
            tk.Label(card, text=label, bg="#0d1428", fg=MUTED,
                     font=("Segoe UI", 10, "bold")).pack()
            var = tk.StringVar(value="—")
            tk.Label(card, textvariable=var, bg="#0d1428", fg=GOLD,
                     font=("Segoe UI", 26, "bold")).pack()
            self.dash_vars[key] = var
        tk.Label(f, text="*Free users never contact the server (privacy) — only activated keys/devices are visible.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(pady=(0, 8))
        tk.Button(f, text="↻ Refresh all", bg=GOLD, fg="black", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=20, pady=6,
                  command=self.refresh_all).pack(pady=4)

    # ── keys ──
    def _tab_keys(self):
        f = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(f, text="  🔑 Keys & Devices  ")
        cols = ("hash", "label", "device", "seen", "version", "status")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        widths = {"hash": 130, "label": 110, "device": 110, "seen": 90, "version": 70, "status": 90}
        for c in cols:
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)
        bar = tk.Frame(f, bg=PANEL)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(bar, text="＋ Generate + Register", bg=GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                  command=self._gen_register).pack(side="left", padx=3)
        tk.Button(bar, text="⛔ Revoke", bg="#7f1d1d", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                  command=lambda: self._set_revoked(True)).pack(side="left", padx=3)
        tk.Button(bar, text="✅ Unrevoke", bg="#14532d", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                  command=lambda: self._set_revoked(False)).pack(side="left", padx=3)
        tk.Button(bar, text="📱 Reset device", bg="#1e3a8a", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                  command=self._reset_device).pack(side="left", padx=3)
        tk.Button(bar, text="🗑 Delete key", bg="#3f3f46", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=5,
                  command=self._delete_key).pack(side="left", padx=3)

    def _selected_hash(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Admin", "Select a key row first.")
            return None
        return self.tree.item(sel[0])["values"][0]

    def _gen_register(self):
        db = self._db_or_warn()
        if db is None:
            return
        from tkinter import simpledialog
        label = simpledialog.askstring("New key", "Buyer note (e.g. buyer name):", parent=self) or ""
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        from alisa.license import make_key, key_hash
        key = make_key(label)
        db.reference(f"keyHashes/{key_hash(key)}").set(
            {"revoked": False, "label": label, "created": int(__import__("time").time())})
        messagebox.showinfo("New key", f"Registered!\n\nSend this to buyer:\n{key}")
        self.refresh_all()

    def _set_revoked(self, val):
        db = self._db_or_warn()
        if db is None:
            return
        h = self._selected_hash()
        if not h:
            return
        # find full hash by prefix
        full = self._resolve_hash(h)
        if not full:
            return
        db.reference(f"keyHashes/{full}/revoked").set(val)
        self.refresh_all()

    def _reset_device(self):
        db = self._db_or_warn()
        if db is None:
            return
        h = self._selected_hash()
        if not h:
            return
        full = self._resolve_hash(h)
        if not full:
            return
        db.reference(f"keyHashes/{full}/device").delete()
        messagebox.showinfo("Admin", "Device binding cleared — key can activate on a new device.")
        self.refresh_all()

    def _delete_key(self):
        db = self._db_or_warn()
        if db is None:
            return
        h = self._selected_hash()
        if not h:
            return
        full = self._resolve_hash(h)
        if not full:
            return
        if messagebox.askyesno("Admin", f"Delete key {h}… permanently?"):
            db.reference(f"keyHashes/{full}").delete()
            self.refresh_all()

    def _cache_hashes(self):
        return getattr(self, "_hash_cache", {})

    def _resolve_hash(self, short):
        for full in self._cache_hashes():
            if full.startswith(short):
                return full
        return None

    # ── updates ──
    def _tab_updates(self):
        f = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(f, text="  🚀 Updates  ")
        tk.Label(f, text="Publish app update (shows 🔔 bell in all user apps):", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        self.upd_ver = self._labeled_entry(f, "Version (e.g. 1.1.0):")
        self.upd_url = self._labeled_entry(f, "Download URL:", "https://github.com/swampodsarkar321/ALISA-AI-BUDDY/releases")
        tk.Label(f, text="What's new (one per line):", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(8, 2))
        self.upd_notes = tk.Text(f, bg="#0d1428", fg=TEXT, font=("Segoe UI", 10),
                                 wrap="word", height=7, relief="flat", padx=10, pady=8)
        self.upd_notes.pack(fill="both", expand=True, padx=14)
        tk.Button(f, text="📢 Publish Update", bg=GOLD, fg="black", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=24, pady=8,
                  command=self._publish_update).pack(pady=10)

    def _labeled_entry(self, parent, label, default=""):
        tk.Label(parent, text=label, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(8, 2))
        e = tk.Entry(parent, font=("Segoe UI", 10), width=60)
        e.pack(anchor="w", padx=14)
        e.insert(0, default)
        return e

    def _publish_update(self):
        db = self._db_or_warn()
        if db is None:
            return
        ver = self.upd_ver.get().strip()
        if not ver:
            messagebox.showwarning("Admin", "Enter a version.")
            return
        db.reference("meta/appcast").set({
            "version": ver,
            "notes": self.upd_notes.get("1.0", "end").strip() or "Bug fixes and improvements.",
            "url": self.upd_url.get().strip(),
        })
        messagebox.showinfo("Admin", f"Update v{ver} published! All apps will show the 🔔 bell.")

    # ── notify ──
    def _tab_notify(self):
        f = tk.Frame(self.notebook, bg=PANEL)
        self.notebook.add(f, text="  📣 Notify  ")
        tk.Label(f, text="Broadcast notice (popup in all user apps, once each):", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        self.ntf_title = self._labeled_entry(f, "Title:")
        tk.Label(f, text="Message:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(8, 2))
        self.ntf_body = tk.Text(f, bg="#0d1428", fg=TEXT, font=("Segoe UI", 10),
                                wrap="word", height=8, relief="flat", padx=10, pady=8)
        self.ntf_body.pack(fill="both", expand=True, padx=14)
        row = tk.Frame(f, bg=PANEL)
        row.pack(pady=10)
        tk.Button(row, text="📣 Send Notice", bg=GOLD, fg="black", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=24, pady=8,
                  command=self._send_notice).pack(side="left", padx=5)
        tk.Button(row, text="Clear Notice", bg="#3f3f46", fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=24, pady=8,
                  command=self._clear_notice).pack(side="left", padx=5)

    def _send_notice(self):
        import time as _t
        db = self._db_or_warn()
        if db is None:
            return
        title = self.ntf_title.get().strip()
        body = self.ntf_body.get("1.0", "end").strip()
        if not title or not body:
            messagebox.showwarning("Admin", "Title and message required.")
            return
        db.reference("meta/announcement").set(
            {"id": f"ann-{int(_t.time())}", "title": title, "body": body})
        messagebox.showinfo("Admin", "Notice sent! It will pop up in user apps.")

    def _clear_notice(self):
        db = self._db_or_warn()
        if db is None:
            return
        db.reference("meta/announcement").delete()
        messagebox.showinfo("Admin", "Notice cleared.")

    # ── refresh ──
    def refresh_all(self):
        if self.db is None:
            return
        try:
            data = self.db.reference("keyHashes").get() or {}
            self._hash_cache = data
            total = len(data)
            active = sum(1 for v in data.values() if isinstance(v, dict) and not v.get("revoked") and v.get("device"))
            revoked = sum(1 for v in data.values() if isinstance(v, dict) and v.get("revoked"))
            self.dash_vars["total"].set(str(total))
            self.dash_vars["active"].set(str(active))
            self.dash_vars["revoked"].set(str(revoked))
            self.dash_vars["free"].set("∞*")
            for row in self.tree.get_children():
                self.tree.delete(row)
            for h, v in sorted(data.items()):
                if not isinstance(v, dict):
                    continue
                self.tree.insert("", "end", values=(
                    h[:12] + "…",
                    str(v.get("label", ""))[:16],
                    str(v.get("device", "—"))[:12],
                    ago(v.get("lastSeen")),
                    str(v.get("appVersion", "—")),
                    "⛔ revoked" if v.get("revoked") else ("💎 bound" if v.get("device") else "🆕 unused"),
                ))
        except Exception as e:
            messagebox.showerror("Admin", f"Refresh failed:\n{e}")


def main():
    AdminApp().mainloop()


if __name__ == "__main__":
    main()
