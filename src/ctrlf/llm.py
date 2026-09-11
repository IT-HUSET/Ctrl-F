"""Thin client for the local model. No external APIs: everything stays on localhost."""
from __future__ import annotations

import json
import requests

from .config import OLLAMA_URL, MODEL


def ask(prompt: str, system: str = "", schema: dict | None = None,
        temperature: float = 0.0, timeout: int = 180) -> str:
    body = {
        "model": MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": 8192},
    }
    if schema:
        body["format"] = schema
    r = requests.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()["response"]


def ask_json(prompt: str, schema: dict, system: str = "", **kw) -> dict:
    raw = ask(prompt, system=system, schema=schema, **kw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise


def available() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).ok
    except Exception:
        return False
