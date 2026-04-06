"""Load API keys from RTF (assignment: no .env in repo)."""

from __future__ import annotations

import re
from pathlib import Path


def parse_keys_rtf(rtf_path: Path) -> dict[str, str]:
    raw = rtf_path.read_text(encoding="utf-8", errors="ignore")
    out: dict[str, str] = {}

    m = re.search(r"React Gemini API Key\s*=\s*([A-Za-z0-9_\-]+)", raw)
    if m:
        out["gemini"] = m.group(1).strip()

    m = re.search(r"ElevenLabs_API_Key\s*=\s*(sk_[a-zA-Z0-9]+)", raw)
    if m:
        out["elevenlabs"] = m.group(1).strip()

    m = re.search(r"OPENAI_API_KEY\s*=\s*(sk-[a-zA-Z0-9\-_]+)", raw)
    if m:
        out["openai"] = m.group(1).strip()

    return out


def default_rtf_path(repo_root: Path) -> Path:
    """API_Key.rtf lives next to the HW folder under Gen AI (sibling of repo root)."""
    return repo_root.parent / "API_Key.rtf"
