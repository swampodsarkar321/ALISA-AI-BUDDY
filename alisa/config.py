"""ALISA local config (API key lives ONLY on this PC)."""

import json
import os
import sys


def app_data_dir():
    """Writable folder: %APPDATA%/ALISA when frozen (.exe), module dir in dev."""
    if getattr(sys, "frozen", False):
        path = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ALISA")
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


CONFIG_PATH = os.path.join(app_data_dir(), "config.json")


def load():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except OSError:
        return False
