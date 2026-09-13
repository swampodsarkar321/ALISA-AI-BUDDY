"""ALISA contacts (name → phone, stored locally)."""

import json
import os
import re

from .config import app_data_dir

CONTACTS_PATH = os.path.join(app_data_dir(), "contacts.json")


def load():
    try:
        with open(CONTACTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return dict(data) if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(contacts):
    try:
        with open(CONTACTS_PATH, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def add(name, number):
    digits = re.sub(r"\D", "", number or "")
    if not name or len(digits) < 8:
        return False
    contacts = load()
    contacts[name.strip().lower()] = digits
    return save(contacts)


def resolve(name_or_number):
    contacts = load()
    key = (name_or_number or "").strip().lower()
    if key in contacts:
        return contacts[key]
    digits = re.sub(r"\D", "", name_or_number or "")
    return digits if len(digits) >= 8 else ""
