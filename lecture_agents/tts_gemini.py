"""Gemini preview TTS: PCM/WAV chunks merged to one MP3 via ffmpeg."""

from __future__ import annotations

import re
import subprocess
import tempfile
import wave
from pathlib import Path

from google import genai
from google.genai import types

# Preview TTS model (see https://ai.google.dev/gemini-api/docs/speech-generation)
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "Kore"
SAMPLE_RATE = 24000
SAMPLE_WIDTH = 2
CHANNELS = 1
MAX_CHARS = 2800


def _split_text_chunks(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for s in re.split(r"(?<=[.!?])\s+", text):
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


def _write_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def _gemini_synthesize_chunk(
    client: genai.Client,
    instruction_and_text: str,
    voice_name: str,
) -> bytes:
    resp = client.models.generate_content(
        model=GEMINI_TTS_MODEL,
        contents=instruction_and_text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    )
                )
            ),
        ),
    )
    cand = resp.candidates[0].content.parts[0]
    inline = getattr(cand, "inline_data", None) or getattr(cand, "inlineData", None)
    if inline is None:
        raise RuntimeError("Gemini TTS returned no inline audio data")
    data = inline.data
    if isinstance(data, str):
        import base64

        data = base64.b64decode(data)
    if not data:
        raise RuntimeError("Empty audio bytes from Gemini TTS")
    return data


def _ffmpeg_wavs_to_mp3(wav_paths: list[Path], out_mp3: Path) -> None:
    if len(wav_paths) == 1:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_paths[0].resolve()),
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "4",
            str(out_mp3.resolve()),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for p in wav_paths:
            safe = p.resolve().as_posix().replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
        lst = Path(f.name)
    try:
        merged = wav_paths[0].parent / "_merged_temp.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-c",
                "copy",
                str(merged.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(merged.resolve()),
                "-codec:a",
                "libmp3lame",
                "-qscale:a",
                "4",
                str(out_mp3.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        merged.unlink(missing_ok=True)
    finally:
        lst.unlink(missing_ok=True)


def synthesize_slide_to_mp3(
    text: str,
    api_key: str,
    out_mp3: Path,
    style_prefix: str = "",
    voice_name: str = DEFAULT_VOICE,
) -> None:
    """Synthesize narration to MP3 using Gemini TTS (requires ffmpeg for MP3 encode)."""
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)
    prefix = (
        style_prefix.strip()
        + "\n\n"
        if style_prefix.strip()
        else ""
    )
    chunks = _split_text_chunks(text)
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        wavs: list[Path] = []
        for i, ch in enumerate(chunks):
            prompt = (
                f"{prefix}"
                "You are recording a university lecture voiceover. "
                "Speak clearly in English. Do not add commentary—read the narration naturally.\n\n"
                f"{ch}"
            )
            pcm = _gemini_synthesize_chunk(client, prompt, voice_name)
            w = tdir / f"chunk_{i:03d}.wav"
            _write_wav(w, pcm)
            wavs.append(w)
        _ffmpeg_wavs_to_mp3(wavs, out_mp3)
