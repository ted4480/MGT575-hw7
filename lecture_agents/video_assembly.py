"""Mux slide PNG + slide MP3, then concat segments (audio-length drives duration)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def mux_slide_audio(
    png_path: Path,
    mp3_path: Path,
    segment_mp4: Path,
) -> None:
    segment_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(png_path.resolve()),
        "-i",
        str(mp3_path.resolve()),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(segment_mp4.resolve()),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def concat_segments(segment_paths: list[Path], out_mp4: Path) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for p in segment_paths:
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
            str(out_mp4.resolve()),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    finally:
        list_path.unlink(missing_ok=True)


def assemble_lecture_video(
    slide_paths: list[Path],
    audio_dir: Path,
    out_mp4: Path,
    work_dir: Path | None = None,
) -> None:
    work_dir = work_dir or (out_mp4.parent / "_segments")
    work_dir.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    for png in slide_paths:
        stem = png.stem  # slide_001
        mp3 = audio_dir / f"{stem}.mp3"
        if not mp3.is_file():
            raise FileNotFoundError(f"Missing audio for {png.name}: {mp3}")
        seg = work_dir / f"{stem}.mp4"
        mux_slide_audio(png, mp3, seg)
        segments.append(seg)
    concat_segments(segments, out_mp4)
