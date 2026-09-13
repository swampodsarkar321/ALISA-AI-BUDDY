# 💜 ALISA — AI Desktop Assistant for Windows

**Voice Commands • AI Automation • Screen Reading • Computer Vision • System Control • Human-Like Voice • Website Generation • Productivity Tools**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/badge/PyPI-alisa--assistant-purple)](https://pypi.org/project/alisa-assistant/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)

## 📖 About ALISA

ALISA is a powerful AI-powered desktop assistant built entirely in Python.

ALISA combines voice interaction, free AI chat, computer vision, screen understanding, system control, website generation, and productivity tools into a single JARVIS-style gold dashboard.

Designed for creators, developers, students and professionals, ALISA works **out of the box** — free OpenRouter AI built in, no setup needed.

## ✨ Core Features

### 🎤 Voice Assistant
- Human-like AI voice (female/male switch)
- Real-time voice conversations + word-synced lip-sync animation
- Speech recognition (mic) + offline text-to-speech
- Multi-language support (English + Bangla, AI-powered)

### 🧠 AI Intelligence
- OpenRouter **free** models built-in (zero setup) + Gemini optional upgrade
- Smart responses with conversation history
- Deep research reports saved to Desktop
- AI memory system (`remember / forget`)
- Free-only model guard (never spends money)

### 👀 Screen Reading & Understanding
- Screenshot capture, OCR text extraction (Tesseract)
- AI screen analysis & summaries
- Active window detection, open-apps list

### 📷 Computer Vision
- Camera snapshots described by AI vision
- Scene understanding, visual Q&A

### ⚙️ Automation Engine
- Open/close apps & sites, smart search
- Command chaining (`open notepad then search cats`)
- Reminders with voice alerts, notes, workflows

### 💻 Windows System Control
- Volume up/down/mute, brightness 10–100
- Minimize/maximize/restore, lock PC
- Keyboard automation (`press`, `type`), mouse click/move
- CPU/RAM/disk monitoring, live dashboard stats

### 📁 File Management
- Notes, folders, move, rename, delete
- Auto-organize folders by type
- Smart file search, file analysis, clipboard read

### 💬 Communication
- WhatsApp messaging (number or saved contact name)
- Contact book, message via wa.me

### 🌐 Internet & Productivity
- News search, Google/YouTube search, web research

### 🌍 Website Generation
- `website NAME [landing|blog|portfolio]` starter scaffolds
- Publish-to-Vercel guidance built in

### 🎨 JARVIS-Style Dashboard
- Animated anime heroine: blinking, talking mouth, emotions (happy/sad/thinking/surprised)
- Orbiting halo, voice waveform, live clock/CPU/RAM/battery/weather
- Tools sidebar, chat + vision tabs, dark gold theme

## 📸 Screenshots

### 🎨 ALISA Dashboard
![ALISA Dashboard](./screenshots/dashboard.png)

### 💬 AI Chat + Tools
![ALISA Chat](./screenshots/chat.png)

### 👁 Vision + Emotions
![ALISA Vision](./screenshots/vision.png)

> Screenshots: run `python main.py`, press `Win + Shift + S`, save as the names above.

## 📦 Installation

### Step 1 — Install Python (3.10+)

Download: **https://www.python.org/downloads/** — tick **Add Python to PATH**.

### Step 2 — Install ALISA

```bat
pip install alisa-assistant
```

### Step 3 — Launch

```bat
alisa
```

### Update / Uninstall

```bat
pip install --upgrade alisa-assistant
pip uninstall alisa-assistant
```

## 🔑 OpenRouter API key setup (2 min, FREE)

ALISA ships with a built-in free key, so it works immediately. To use your **own** key (recommended for heavy use):

1. Go to **openrouter.ai/keys** → sign in → **Create Key** (free, no card needed)
2. Copy the key (starts with `sk-or-v1-...`)
3. Open ALISA → **⚙ Settings** → paste into **OpenRouter key** → **Save**
4. Done! Only **free models** (`:free`) are ever used — you'll never be charged.

> Your key stays on your own PC (config.json). Never share it publicly.
> For Gemini instead: free key at **aistudio.google.com** → same Settings box.

## 💎 Premium — ৳150 lifetime

Premium unlocks **Camera Vision + Deep Research + Website Generator**, forever.

**How to buy:**
1. Message **[@swampod on Telegram](https://t.me/swampod)** — send **৳150 via bKash**
2. Receive your `ALISA-XXXX-...` activation key
3. Open ALISA → **Activation Center** (top bar) → paste key → **Activate ✨**

## 🚀 Run from source

```bat
cd D:\ALISA
pip install -r requirements.txt
python main.py
```

Tesseract OCR program also needed for screen reading:
**github.com/UB-Mannheim/tesseract/wiki** (`tesseract-ocr-w64-setup.exe`)

## 📂 Project Structure

```
ALISA/
├── main.py            → local launcher (python main.py)
├── pyproject.toml     → PyPI packaging (`alisa` command)
├── requirements.txt
├── screenshots/       → dashboard screenshots
├── README.md
├── LICENSE
└── alisa/
    ├── gui.py         → JARVIS dashboard
    ├── hero.py        → animated heroine
    ├── brain.py       → command parser (60+ commands)
    ├── ai_client.py   → OpenRouter-free + Gemini
    ├── voice.py       → TTS/STT + lip-sync
    ├── systemctl.py   → volume/brightness/input automation
    ├── memory.py      → long-term facts
    ├── contacts.py    → WhatsApp contacts
    ├── config.py      → local settings
    └── cli.py         → `alisa` entry point
```

## 🛠 Technologies Used

Python · OpenRouter · Gemini AI · Speech Recognition · Text-To-Speech · OCR · Computer Vision · Windows APIs · tkinter · Threading

## 👨‍💻 Developer

**🚀 Swampod Sarkar** — Creator of ALISA AI Assistant

## 🤝 Contributing

Contributions, issues and feature requests are welcome: fork → branch → commit → pull request.

## 📜 License

MIT License — see [LICENSE](./LICENSE).

---
❤️ Built with Python & AI · Developed by **Swampod Sarkar**
