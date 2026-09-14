"""ALISA core: command parsing + execution (100% original)."""

import datetime
import os
import random
import re
import shutil
import subprocess
import threading
import time
import webbrowser

from . import contacts
from . import license as lic
from .memory import load_facts, remember, forget

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "I told my computer I needed a break — now it won't stop sending me KitKat ads.",
    "Why did the developer go broke? He used up all his cache!",
    "My computer and I have a great relationship. I type, it judges silently.",
    "Why do Java developers wear glasses? Because they don't C#!",
    "I would tell you a UDP joke, but you might not get it.",
]

APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "chrome": None,  # resolved via start
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "facebook": "https://www.facebook.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "maps": "https://maps.google.com",
}


def _open_target(target):
    target = (target or "").strip()
    if not target:
        return "Tell me what to open — e.g. 'open notepad' or 'open youtube'."
    low = target.lower()
    for name, dest in APPS.items():
        if name in low:
            if dest is None:  # chrome via start menu
                os.system("start chrome")
            elif dest.startswith("http"):
                webbrowser.open(dest)
            else:
                try:
                    os.startfile(dest)
                except OSError:
                    subprocess.Popen(dest, shell=True)
            return f"Opening {name}..."
    if "." in target and " " not in target:
        url = target if target.startswith("http") else "https://" + target
        webbrowser.open(url)
        return f"Opening {url}..."
    webbrowser.open(f"https://www.google.com/search?q={target}")
    return f"Searching Google for '{target}'..."


def _grab_screen():
    """Returns (path, None) or '!error' string."""
    try:
        from PIL import ImageGrab
    except ImportError:
        return "!Screenshot needs: pip install pillow"
    try:
        path = os.path.join(
            os.path.expanduser("~"), "Desktop",
            f"alisa-shot-{datetime.datetime.now():%Y%m%d-%H%M%S}.png",
        )
        ImageGrab.grab().save(path)
        return (path, None)
    except Exception as e:
        return f"!Screenshot failed: {e}"


def _snap_camera():
    """Capture webcam frame to temp jpg. Returns path or '!error' string."""
    try:
        import cv2
    except ImportError:
        return "!Camera needs: pip install opencv-python"
    try:
        cam = cv2.VideoCapture(0)
        if not cam.isOpened():
            return "!Could not open camera."
        time.sleep(0.6)
        ok, frame = cam.read()
        cam.release()
        if not ok:
            return "!Camera captured nothing."
        path = os.path.join(os.path.expanduser("~"), "Desktop", "alisa-see.jpg")
        cv2.imwrite(path, frame)
        return path
    except Exception as e:
        return f"!Camera failed: {e}"


def _site_template(name, kind):
    hero = {
        "landing": "<div class='wrap'><h1>Welcome to " + name + " 🚀</h1><p>Your landing page. Edit me!</p><div class='card'><h2>Features</h2><ul><li>Fast</li><li>Beautiful</li><li>Yours</li></ul></div></div>",
        "blog": "<div class='wrap'><h1>" + name + " Blog ✍️</h1><div class='card'><h2>First post</h2><p>Hello world — write here.</p><small>2026-01-01</small></div></div>",
        "portfolio": "<div class='wrap'><h1>" + name + " 🎨</h1><p>Designer & developer.</p><div class='card'><h2>Projects</h2><ul><li>Project One</li><li>Project Two</li></ul></div><div class='card'><h2>Contact</h2><p>Mail me: hello@example.com</p></div></div>",
    }[kind]
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        "  <meta charset=\"utf-8\" />\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
        f"  <title>{name}</title>\n  <link rel=\"stylesheet\" href=\"style.css\" />\n"
        "</head>\n<body>\n" + hero + "\n</body>\n</html>\n"
    )


def handle_command(text, system):
    """Entry point. Supports chaining with 'then' / 'and then'."""
    t = (text or "").strip()
    for sep in (" and then ", " then "):
        if sep in t.lower():
            parts = [p.strip() for p in re.split(sep, t, flags=re.I) if p.strip()][:4]
            if len(parts) > 1:
                done, ai_part = [], None
                for p in parts:
                    reply, use_ai = _single(p, system)
                    if use_ai:
                        ai_part = p
                    elif reply:
                        done.append(reply)
                if ai_part and not done:
                    return "", True
                if ai_part:
                    return ("\n".join(done) + f"\n@@AI:{ai_part}", False)
                return ("\n".join(done), False)
    return _single(text, system)


def _single(text, system):
    t = (text or "").strip()
    low = t.lower()
    if not low:
        return "Say something first!", False
    is_bn = bool(re.search(r'[\u0980-\u09FF]', t))

    if low in ("hi", "hello", "hey", "salam", "assalamu alaikum", "হাই", "হ্যালো", "সালাম", "আদাব"):
        if is_bn:
            return ("আসসালামু আলাইকুম! আমি ALISA। 'help' লিখলে সব কাজ দেখতে পাবে।", False)
        hour = datetime.datetime.now().hour
        greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        return f"{greet}! I'm ALISA. Try 'help' to see what I can do.", False

    if low in ("help", "what can you do", "commands"):
        return (
            "Here's what I can do:\n"
            "• open [app/site] · close [app] — notepad, calculator, youtube…\n"
            "• search [topic] · play [song] · news [topic]\n"
            "• time / date\n"
            "• volume up | down | mute | unmute\n"
            "• brightness 10–100\n"
            "• note [text] · make folder [name] · list files\n"
            "• rename [old] to [new] · delete file [name]\n"
            "• clipboard — read what's copied\n"
            "• press [key] · type [text] · click · move mouse X Y\n"
            "• minimize · maximize · restore · list windows · lock pc\n"
            "• screenshot · read screen · analyze screen\n"
            "• whatsapp [number] [message]\n"
            "• website [name] — scaffold a starter site\n"
            "• remind me in [N] minutes [message]\n"
            "• system info · joke\n"
            "• anything else → I ask Gemini AI ✨"
        ), False

    if low.startswith("open "):
        return _open_target(t[5:]), False

    if low.startswith("close "):
        app = t[6:].strip().lower()
        mapping = {"notepad": "notepad.exe", "calculator": "calc.exe", "paint": "mspaint.exe",
                   "chrome": "chrome.exe", "edge": "msedge.exe", "firefox": "firefox.exe"}
        exe = mapping.get(app, app if app.endswith(".exe") else app + ".exe")
        try:
            subprocess.run(["taskkill", "/f", "/im", exe],
                           capture_output=True, timeout=10)
            return (f"Closed {app}.", False)
        except Exception as e:
            return (f"Could not close {app}: {e}", False)

    if low.startswith("search "):
        q = t[7:].strip()
        webbrowser.open(f"https://www.google.com/search?q={q}")
        return f"Searching Google for '{q}'...", False

    if low.startswith("play "):
        q = t[5:].strip()
        webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
        return f"Playing '{q}' on YouTube...", False

    if low == "news" or low.startswith("news "):
        q = t[4:].strip()
        url = "https://news.google.com" if not q else f"https://news.google.com/search?q={q}"
        webbrowser.open(url)
        return ("Opening Google News..." if not q else f"Showing news about '{q}'..."), False

    if low.startswith("whatsapp "):
        parts = t[9:].strip().split(maxsplit=1)
        number = "".join(c for c in (parts[0] if parts else "") if c.isdigit())
        msg = parts[1] if len(parts) > 1 else ""
        if not number:
            return ("Give a number, e.g. 'whatsapp 8801XXXXXXXXX hello'.", False)
        from urllib.parse import quote
        url = f"https://wa.me/{number}" + (f"?text={quote(msg)}" if msg else "")
        webbrowser.open(url)
        return ("Opening WhatsApp chat...", False)

    if "time" in low and len(low.split()) <= 3:
        now = datetime.datetime.now().strftime("%I:%M %p")
        return f"It's {now}.", False

    if "date" in low and len(low.split()) <= 3:
        today = datetime.datetime.now().strftime("%A, %d %B %Y")
        return f"Today is {today}.", False

    if low.startswith("volume"):
        if "mute" in low and "unmute" not in low:
            return system.set_mute(True)
        if "unmute" in low:
            return system.set_mute(False)
        if "up" in low:
            return system.volume_delta(+10)
        if "down" in low:
            return system.volume_delta(-10)
        return ("Say 'volume up', 'volume down', 'volume mute' or 'volume unmute'.", False)

    if low.startswith("brightness"):
        parts = low.split()
        try:
            level = max(10, min(100, int(parts[1])))
            return system.set_brightness(level)
        except (IndexError, ValueError):
            return ("Give a level 10–100, e.g. 'brightness 70'.", False)

    if low.startswith("note "):
        note = t[5:].strip()
        if not note:
            return ("Write something after 'note'.", False)
        path = os.path.join(os.path.expanduser("~"), "Desktop", "alisa-note.txt")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M}] {note}\n")
            return (f"Saved to Desktop\\alisa-note.txt.", False)
        except OSError as e:
            return (f"Could not save note: {e}", False)

    if low.startswith("make folder "):
        name = t[12:].strip() or "alisa-folder"
        path = os.path.join(os.getcwd(), name)
        try:
            os.makedirs(path, exist_ok=True)
            return (f"Folder created: {path}", False)
        except OSError as e:
            return (f"Could not create folder: {e}", False)

    if low.startswith("list files"):
        try:
            items = sorted(os.listdir(os.getcwd()))[:20]
            return ("Files here:\n• " + "\n• ".join(items) if items else "Folder is empty.", False)
        except OSError as e:
            return (f"Could not list files: {e}", False)

    if low.startswith("rename "):
        rest = t[7:].strip()
        if " to " not in rest:
            return ("Say 'rename OLD to NEW'.", False)
        old, new = [x.strip() for x in rest.split(" to ", 1)]
        try:
            os.rename(os.path.join(os.getcwd(), old), os.path.join(os.getcwd(), new))
            return (f"Renamed '{old}' → '{new}'.", False)
        except OSError as e:
            return (f"Rename failed: {e}", False)

    if low.startswith("delete file "):
        name = t[12:].strip()
        path = os.path.join(os.getcwd(), name)
        if not os.path.isfile(path):
            return (f"No such file here: '{name}'.", False)
        try:
            os.remove(path)
            return (f"Deleted '{name}'.", False)
        except OSError as e:
            return (f"Delete failed: {e}", False)

    if low == "clipboard":
        try:
            import tkinter
            root = tkinter.Tk()
            root.withdraw()
            content = root.clipboard_get()
            root.destroy()
            preview = content[:200] + ("…" if len(content) > 200 else "")
            return (f"Clipboard holds:\n{preview}", False)
        except Exception:
            return ("Clipboard is empty or unreadable.", False)

    if low == "screenshot":
        try:
            from PIL import ImageGrab
            path = os.path.join(
                os.path.expanduser("~"), "Desktop",
                f"alisa-shot-{datetime.datetime.now():%Y%m%d-%H%M%S}.png",
            )
            ImageGrab.grab().save(path)
            return (f"Screenshot saved to Desktop.", False)
        except ImportError:
            return ("Screenshot needs: pip install pillow", False)
        except Exception as e:
            return (f"Screenshot failed: {e}", False)

    if low.startswith("remind me in "):
        rest = t[13:].strip().split(maxsplit=1)
        try:
            minutes = float(rest[0])
            msg = rest[1] if len(rest) > 1 else "Time's up!"
            if not 0 < minutes <= 24 * 60:
                raise ValueError
        except (ValueError, IndexError):
            return ("Say 'remind me in 10 take a break'.", False)
        def _remind(m=msg):
            time.sleep(minutes * 60)
            try:
                from .voice import Voice
                Voice().speak(f"Reminder: {m}")
            except Exception:
                pass
        threading.Thread(target=_remind, daemon=True).start()
        return (f"Reminder set for {minutes:g} minute(s) from now.", False)

    if low in ("system info", "pc info", "performance"):
        import platform
        info = [f"System: {platform.system()} {platform.release()}", f"CPU cores: {os.cpu_count()}"]
        try:
            import psutil
            info.append(f"RAM: {psutil.virtual_memory().percent}% used")
            info.append(f"Disk: {psutil.disk_usage('/').percent}% used")
        except ImportError:
            info.append("(pip install psutil for RAM/disk stats)")
        return ("\n".join(info), False)

    if "joke" in low:
        return random.choice(JOKES), False

    if low in ("who are you", "your name", "about you"):
        return ("I'm ALISA — your offline-first desktop assistant, created by Swampod Sarkar. Voice, system control and AI, all in one.", False)

    if any(k in low for k in ("who made you", "who created you", "your creator",
                              "your developer", "tmk ke", "tomake ke", "তোমাকে কে",
                              "baniyeche", "নির্মাতা", "who is your boss")):
        return ("I was created by Swampod Sarkar. 💜", False)

    if low in ("bye", "goodbye", "exit", "quit"):
        return ("Goodbye! See you soon.", False)

    # ── memory ──
    if low.startswith("remember "):
        fact = t[9:].strip()
        if not fact:
            return ("Tell me what to remember, e.g. 'remember my birthday is 5 May'.", False)
        remember(fact)
        return (f"Got it — I'll remember: {fact}", False)

    if low.startswith("forget "):
        if forget(t[7:].strip()):
            return ("Forgotten!", False)
        return ("I couldn't find that memory.", False)

    if low in ("what do you remember", "my memories", "list memories"):
        facts = load_facts()
        if not facts:
            return ("I don't remember anything yet. Say 'remember …' to teach me.", False)
        return ("Here's what I remember:\n• " + "\n• ".join(facts), False)

    # ── deep research (handled by GUI with AI) ──
    if low.startswith("deep research "):
        if not lic.is_premium():
            return lic.premium_required("Deep Research")
        topic = t[14:].strip()
        if not topic:
            return ("Tell me the topic, e.g. 'deep research black holes'.", False)
        return (f"@@RESEARCH:{topic}", False)

    # ── window & screen ──
    if low in ("minimize", "minimize window"):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            ctypes.windll.user32.ShowWindow(hwnd, 6)
            return ("Window minimized.", False)
        except Exception as e:
            return (f"Minimize failed: {e}", False)

    if low in ("lock pc", "lock computer", "lock"):
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return ("PC locked. 🔒", False)

    if low in ("active window", "what is open", "current window"):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return (f"Active window: {buf.value or '(untitled)'}", False)
        except Exception as e:
            return (f"Could not read window: {e}", False)

    if low in ("read screen", "what is on my screen", "ocr"):
        shot = _grab_screen()
        if isinstance(shot, str) and shot.startswith("!"):
            return (shot[1:], False)
        path, _img = shot
        try:
            import pytesseract
            from PIL import Image
            try:
                text = pytesseract.image_to_string(Image.open(path)).strip()
            except Exception:
                # binary missing from PATH? try default Windows install locations
                found = ""
                for cand in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                             r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
                    if os.path.isfile(cand):
                        found = cand
                        break
                if not found:
                    raise
                pytesseract.pytesseract.tesseract_cmd = found
                text = pytesseract.image_to_string(Image.open(path)).strip()
            os.remove(path)
            if not text:
                return ("Screen captured, but no readable text found.", False)
            return ("Here's the text on your screen:\n" + text[:800], False)
        except ImportError:
            return ("OCR needs: pip install pytesseract pillow", False)
        except Exception:
            return ("Tesseract program missing. Install it free: github.com/UB-Mannheim/tesseract/wiki "
                    "(tesseract-ocr-w64-setup.exe) → Next-Next-Install → restart ALISA.", False)

    # ── camera vision (handled by GUI with AI) ──
    if low in ("see", "look", "what do you see", "camera", "open camera"):
        if not lic.is_premium():
            return lic.premium_required("Camera Vision")
        snap = _snap_camera()
        if isinstance(snap, str) and snap.startswith("!"):
            return (snap[1:], False)
        return (f"@@VISION:{snap}", False)

    # ── files+ ──
    if low.startswith("move ") and not low.startswith("move mouse "):
        rest = t[5:].strip()
        if " to " not in rest:
            return ("Say 'move FILE to FOLDER'.", False)
        src, dst = [x.strip() for x in rest.split(" to ", 1)]
        try:
            src_p = os.path.join(os.getcwd(), src)
            dst_p = os.path.join(os.getcwd(), dst)
            if os.path.isdir(dst_p):
                dst_p = os.path.join(dst_p, os.path.basename(src_p))
            shutil.move(src_p, dst_p)
            return (f"Moved to {dst_p}.", False)
        except Exception as e:
            return (f"Move failed: {e}", False)

    if low in ("organize", "organize folder", "clean folder"):
        try:
            base = os.getcwd()
            moved = 0
            for item in os.listdir(base):
                p = os.path.join(base, item)
                if os.path.isfile(p) and not item.startswith("."):
                    ext = (os.path.splitext(item)[1] or ".misc").lstrip(".").lower()
                    folder = os.path.join(base, f"organized-{ext}")
                    os.makedirs(folder, exist_ok=True)
                    shutil.move(p, os.path.join(folder, item))
                    moved += 1
            return (f"Organized {moved} file(s) into folders.", False)
        except Exception as e:
            return (f"Organize failed: {e}", False)

    if low.startswith("find file "):
        name = t[10:].strip().lower()
        hits = []
        roots = [os.getcwd(), os.path.join(os.path.expanduser("~"), "Desktop")]
        try:
            for root in roots:
                for dirpath, _dirs, files in os.walk(root):
                    for f in files:
                        if name in f.lower():
                            hits.append(os.path.join(dirpath, f))
                            if len(hits) >= 10:
                                break
                    if len(hits) >= 10:
                        break
            if not hits:
                return (f"No file matching '{name}' in working folder/Desktop.", False)
            return ("Found:\n• " + "\n• ".join(hits), False)
        except Exception as e:
            return (f"Search failed: {e}", False)

    if low.startswith("file info "):
        path = os.path.join(os.getcwd(), t[10:].strip())
        if not os.path.exists(path):
            return (f"Not found: '{t[10:].strip()}'.", False)
        try:
            st = os.stat(path)
            lines = [f"Path: {path}", f"Size: {st.st_size:,} bytes",
                     f"Modified: {datetime.datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M}"]
            if os.path.isfile(path) and st.st_size < 200_000:
                try:
                    with open(path, "r", encoding="utf-8", errors="strict") as f:
                        content = f.read()
                    lines.append(f"Lines: {content.count(chr(10)) + 1}, Words: {len(content.split())}")
                except (UnicodeDecodeError, ValueError):
                    lines.append("Type: binary file")
            return ("\n".join(lines), False)
        except OSError as e:
            return (f"Info failed: {e}", False)

    # ── contacts ──
    if low.startswith("add contact "):
        rest = t[12:].strip().rsplit(maxsplit=1)
        if len(rest) < 2 or not contacts.add(rest[0], rest[1]):
            return ("Say 'add contact NAME NUMBER', e.g. 'add contact Rafi 8801XXXXXXXXX'.", False)
        return (f"Contact '{rest[0]}' saved.", False)

    if low in ("contacts", "list contacts", "my contacts"):
        book = contacts.load()
        if not book:
            return ("No contacts yet. Say 'add contact NAME NUMBER'.", False)
        return ("Contacts:\n• " + "\n• ".join(f"{k.title()}: {v}" for k, v in book.items()), False)

    if low.startswith("message "):
        rest = t[8:].strip().split(maxsplit=1)
        if not rest:
            return ("Say 'message NAME your text here'.", False)
        number = contacts.resolve(rest[0])
        if not number:
            return (f"No contact '{rest[0]}'. Add with 'add contact {rest[0]} NUMBER'.", False)
        from urllib.parse import quote
        msg = quote(rest[1]) if len(rest) > 1 else ""
        webbrowser.open(f"https://wa.me/{number}" + (f"?text={msg}" if msg else ""))
        return (f"Opening WhatsApp chat with {rest[0].title()}...", False)

    # ── website templates + publish ──
    if low.startswith("website "):
        if not lic.is_premium():
            return lic.premium_required("Website Generator")
        parts = t[8:].strip().split()
        if not parts:
            return ("Say 'website NAME [landing|blog|portfolio]'.", False)
        name = "".join(c for c in parts[0].lower().replace(" ", "-") if c.isalnum() or c == "-") or "my-site"
        kind = (parts[1].lower() if len(parts) > 1 else "landing")
        if kind not in ("landing", "blog", "portfolio"):
            kind = "landing"
        try:
            base = os.path.join(os.getcwd(), name)
            os.makedirs(base, exist_ok=True)
            with open(os.path.join(base, "index.html"), "w", encoding="utf-8") as f:
                f.write(_site_template(name, kind))
            with open(os.path.join(base, "style.css"), "w", encoding="utf-8") as f:
                f.write("body{font-family:system-ui;margin:0;background:#0f1222;color:#e8eaf6}\n.wrap{max-width:800px;margin:auto;padding:3rem 1rem}\n.card{background:#171b33;border-radius:1rem;padding:1.5rem;margin:1rem 0}\na{color:#a855f7}\n")
            return (f"{kind.title()} site scaffold created in .\\{name}\\ — open index.html! Say 'publish' for hosting steps.", False)
        except OSError as e:
            return (f"Website creation failed: {e}", False)

    if low in ("publish", "how to publish", "deploy website", "hosting"):
        return (
            "To publish a website free:\n"
            "1. Push the folder to GitHub (git init → add → commit → push)\n"
            "2. Go to vercel.com → Add New → Project → Import repo\n"
            "3. Click Deploy — you get a live https link in ~1 minute!\n"
            "Want me to write the exact commands? Just ask the AI.", False)

    if low in ("bye", "goodbye", "exit", "quit"):
        return ("Goodbye! See you soon.", False)

    # ── input automation (keyboard / mouse / windows) ──
    if low.startswith("move mouse "):
        try:
            x, y = t[10:].strip().replace(",", " ").split()[:2]
            return system.mouse_move(int(x), int(y))
        except (ValueError, IndexError):
            return ("Say 'move mouse 500 300'.", False)

    if low.startswith("press "):
        return system.press_key(t[6:].strip())

    if low.startswith("type "):
        return system.type_text(t[5:])

    if low == "click":
        return system.mouse_click()

    if low == "maximize":
        return system.window_show("max")

    if low == "restore":
        return system.window_show("restore")

    if low in ("list windows", "open windows", "running apps"):
        apps = system.list_windows()
        if not apps:
            return ("Could not list windows.", False)
        return ("Running apps:\n• " + "\n• ".join(apps[:18]), False)

    # ── screen analysis (OCR → AI summary, handled by GUI) ──
    if low in ("analyze screen", "summarize screen", "explain screen"):
        shot = _grab_screen()
        if isinstance(shot, str) and shot.startswith("!"):
            return (shot[1:], False)
        path, _img = shot
        try:
            import pytesseract
            from PIL import Image
            text = pytesseract.image_to_string(Image.open(path)).strip()
            os.remove(path)
            if not text:
                return ("Screen captured, but no readable text found.", False)
            return (f"@@ANALYZE:{text[:1500]}", False)
        except ImportError:
            return ("Analysis needs: pip install pytesseract pillow + Tesseract program.", False)
        except Exception as e:
            return (f"Screen analysis failed: {e}", False)

    # ── bare-word usage hints (trailing space gets stripped) ──
    _BARE_HINTS = {
        "remember": "Say 'remember ...', e.g. 'remember my birthday is 5 May'.",
        "note": "Say 'note ...', e.g. 'note buy milk'.",
        "search": "Say 'search ...', e.g. 'search cats'.",
        "play": "Say 'play ...', e.g. 'play faded'.",
        "open": "Say 'open ...', e.g. 'open notepad'.",
        "close": "Say 'close ...', e.g. 'close notepad'.",
        "press": "Say 'press ...', e.g. 'press enter'.",
        "type": "Say 'type ...', e.g. 'type hello'.",
        "move": "Say 'move FILE to FOLDER' or 'move mouse X Y'.",
        "website": "Say 'website NAME [landing|blog|portfolio]'. (Premium feature 🔒)",
        "whatsapp": "Say 'whatsapp NUMBER message'.",
        "brightness": "Say 'brightness 10-100', e.g. 'brightness 70'.",
        "remind": "Say 'remind me in 10 take a break'.",
        "message": "Say 'message NAME your text here'.",
    }
    if low in _BARE_HINTS:
        return (_BARE_HINTS[low], False)

    # ── owner knowledge base (taught from admin panel) ──
    try:
        from .knowledge import cached_entries, find_answer
        _kb_hit = find_answer(t, cached_entries())
        if _kb_hit:
            return (_kb_hit, False)
    except Exception:
        pass

    return "", True  # fall through to Gemini AI
