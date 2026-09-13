"""ALISA long-term memory (facts about the user, stored locally)."""

import json
import os

from .config import app_data_dir

MEM_PATH = os.path.join(app_data_dir(), "memory.json")


def load_facts():
    try:
        with open(MEM_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            facts = data.get("facts", [])
            return [str(x) for x in facts if str(x).strip()][:50]
    except (OSError, ValueError):
        return []


def save_facts(facts):
    try:
        with open(MEM_PATH, "w", encoding="utf-8") as f:
            json.dump({"facts": facts[:50]}, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def remember(sentence):
    facts = load_facts()
    s = sentence.strip()
    if s and s not in facts:
        facts.append(s)
        save_facts(facts)
        return True
    return False


def forget(keyword):
    facts = load_facts()
    kept = [f for f in facts if keyword.lower() not in f.lower()]
    if len(kept) == len(facts):
        return False
    save_facts(kept)
    return True
