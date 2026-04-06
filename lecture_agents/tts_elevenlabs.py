"""ElevenLabs TTS with chunking + ffmpeg concat into one MP3 per slide."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import requests

# Default voice; override with --elevenlabs-voice-id if needed
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
ELEVEN_MODEL = "eleven_multilingual_v2"
MAX_CHARS = 3500


def _split_text_chunks(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for s in sentences:
        if not s:
            continue
        if size + len(s) + 1 > max_chars and buf:
            parts.append(" ".join(buf).strip())
            buf = [s]
            size = len(s)
        else:
            buf.append(s)
            size += len(s) + 1
    if buf:
        parts.append(" ".join(buf).strip())
    return parts


def _synthesize_chunk(text: str, api_key: str, voice_id: str, out_mp3: Path) -> None:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "model_id": ELEVEN_MODEL,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    out_mp3.write_bytes(r.content)


def _ffmpeg_concat_mp3(parts: list[Path], out_path: Path) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for p in parts:
            # concat demuxer requires: file 'path'
            safe = p.resolve().as_posix().replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
        list_path = Path(f.name)
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    finally:
        list_path.unlink(missing_ok=True)


def synthesize_slide_to_mp3(
    text: str,
    api_key: str,
    out_mp3: Path,
    voice_id: str = DEFAULT_VOICE_ID,
) -> None:
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    chunks = _split_text_chunks(text)
    if len(chunks) == 1:
        _synthesize_chunk(chunks[0], api_key, voice_id, out_mp3)
        return
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        parts: list[Path] = []
        for i, ch in enumerate(chunks):
            part = tdir / f"part_{i:03d}.mp3"
            _synthesize_chunk(ch, api_key, voice_id, part)
            parts.append(part)
        _ffmpeg_concat_mp3(parts, out_mp3)
