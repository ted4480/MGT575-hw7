#!/usr/bin/env python3
"""
Entrypoint: PDF lecture deck -> style.json, structured JSON agents, per-slide MP3, final MP4.

API keys: pass --keys-file (default: ../API_Key.rtf relative to repo = Gen AI/API_Key.rtf).
Do not commit API_Key.rtf or any .env (per assignment).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from lecture_agents.api_keys import default_rtf_path, parse_keys_rtf
from lecture_agents.arc_agent import build_arc_json
from lecture_agents.gemini_client import GeminiClient
from lecture_agents.narration_agent import build_slide_narrations
from lecture_agents.pdf_slides import rasterize_pdf_to_pngs
from lecture_agents.premise_agent import build_premise_json
from lecture_agents.slide_description_agent import describe_slides_chained
from lecture_agents.style_agent import build_style_json
from lecture_agents.tts_elevenlabs import DEFAULT_VOICE_ID, synthesize_slide_to_mp3 as elevenlabs_tts
from lecture_agents.tts_gemini import synthesize_slide_to_mp3 as gemini_tts
from lecture_agents.video_assembly import assemble_lecture_video


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _require_ffmpeg() -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        raise SystemExit(
            "ffmpeg is required for audio merge and video assembly. Install ffmpeg and ensure "
            "it is on your PATH (e.g. `brew install ffmpeg` on macOS)."
        ) from e


def main() -> None:
    parser = argparse.ArgumentParser(description="Agentic lecture video pipeline")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Repository root (contains PDF, requirements, projects/)",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Lecture PDF path (default: <repo>/Lecture_17_AI_screenplays.pdf)",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=None,
        help="Instructor transcript (default: <repo>/Input/instructor_lecture_transcript.txt)",
    )
    parser.add_argument(
        "--keys-file",
        type=Path,
        default=None,
        help="RTF file with Gemini / ElevenLabs keys (default: sibling Gen AI/API_Key.rtf)",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-2.5-flash",
        help="Gemini model id for agents",
    )
    parser.add_argument(
        "--elevenlabs-voice-id",
        default=None,
        help="Override ElevenLabs voice id (default: built-in Rachel voice id)",
    )
    parser.add_argument(
        "--tts-provider",
        choices=["gemini", "elevenlabs", "auto"],
        default="gemini",
        help="TTS backend: gemini (default), elevenlabs, or auto (ElevenLabs then Gemini on failure)",
    )
    parser.add_argument(
        "--gemini-tts-voice",
        default="Kore",
        help="Prebuilt Gemini TTS voice name (see Google speech-generation docs)",
    )
    parser.add_argument(
        "--skip-style",
        action="store_true",
        help="Do not regenerate style.json if it already exists",
    )
    parser.add_argument(
        "--stop-before-audio",
        action="store_true",
        help="Stop after writing slide_description_narration.json (no TTS/video)",
    )
    parser.add_argument(
        "--stop-before-video",
        action="store_true",
        help="Generate MP3s but skip final MP4 mux/concat",
    )
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    pdf = (args.pdf or repo / "Lecture_17_AI_screenplays.pdf").resolve()
    transcript = (
        args.transcript or repo / "Input" / "instructor_lecture_transcript.txt"
    ).resolve()
    keys_path = (args.keys_file or default_rtf_path(repo)).resolve()

    if not pdf.is_file():
        raise SystemExit(f"PDF not found: {pdf}")
    if not transcript.is_file():
        raise SystemExit(
            f"Transcript not found: {transcript}\n"
            "Add instructor_lecture_transcript.txt under Input/ (see README)."
        )
    if not keys_path.is_file():
        raise SystemExit(
            f"Keys RTF not found: {keys_path}\n"
            "Pass --keys-file with the path to API_Key.rtf (not committed to GitHub)."
        )

    keys = parse_keys_rtf(keys_path)
    gemini_key = keys.get("gemini") or ""
    eleven_key = keys.get("elevenlabs") or ""
    if not gemini_key:
        raise SystemExit("No Gemini key found in keys RTF (expected 'React Gemini API Key = ...').")
    if args.tts_provider == "elevenlabs" and not eleven_key and not args.stop_before_audio:
        raise SystemExit(
            "ElevenLabs selected but no ElevenLabs_API_Key in keys RTF. "
            "Use --tts-provider gemini or add the key."
        )

    style_path = repo / "style.json"
    if args.skip_style and style_path.is_file():
        style = json.loads(style_path.read_text(encoding="utf-8"))
        print(f"Using existing {style_path.name}")
    else:
        print("Running style agent on transcript...")
        gemini = GeminiClient(gemini_key, model=args.gemini_model)
        style = build_style_json(transcript, gemini)
        _write_json(style_path, style)
        print(f"Wrote {style_path}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_dir = repo / "projects" / f"project_{stamp}"
    slide_img_dir = project_dir / "slide_images"
    audio_dir = project_dir / "audio"
    slide_img_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    print(f"Project directory: {project_dir}")

    print("Rasterizing PDF...")
    slide_paths = rasterize_pdf_to_pngs(pdf, slide_img_dir)
    print(f"Wrote {len(slide_paths)} slide PNGs")

    gemini = GeminiClient(gemini_key, model=args.gemini_model)

    print("Slide description agent (chained context)...")
    slide_desc_doc = describe_slides_chained(slide_paths, gemini)
    _write_json(project_dir / "slide_description.json", slide_desc_doc)

    print("Premise agent...")
    premise = build_premise_json(slide_desc_doc, gemini)
    _write_json(project_dir / "premise.json", premise)

    print("Arc agent...")
    arc = build_arc_json(premise, slide_desc_doc, gemini)
    _write_json(project_dir / "arc.json", arc)

    print("Narration agent...")
    narr_doc = build_slide_narrations(
        slide_paths, style, premise, arc, slide_desc_doc, gemini
    )
    _write_json(project_dir / "slide_description_narration.json", narr_doc)

    if args.stop_before_audio:
        print("Stopping before audio (--stop-before-audio). Done.")
        return

    _require_ffmpeg()

    style_prefix = ""
    if isinstance(style, dict):
        lines = style.get("narrator_guidelines_for_tts")
        if isinstance(lines, list):
            style_prefix = "Speaking style guidelines:\n" + "\n".join(
                f"- {x}" for x in lines if isinstance(x, str)
            )

    def synth_one(idx: int, text: str, out_mp3: Path, provider: str) -> None:
        if provider == "gemini":
            gemini_tts(
                text,
                gemini_key,
                out_mp3,
                style_prefix=style_prefix,
                voice_name=args.gemini_tts_voice,
            )
        else:
            elevenlabs_tts(
                text,
                eleven_key,
                out_mp3,
                voice_id=args.elevenlabs_voice_id or DEFAULT_VOICE_ID,
            )

    provider = args.tts_provider
    if provider == "auto":
        provider = "elevenlabs" if eleven_key else "gemini"

    print(f"TTS ({provider}) per slide...")
    for slide in narr_doc["slides"]:
        idx = slide["slide_index"]
        text = slide["narration"]
        out_mp3 = audio_dir / f"slide_{idx:03d}.mp3"
        try:
            if provider == "elevenlabs":
                synth_one(idx, text, out_mp3, "elevenlabs")
            else:
                synth_one(idx, text, out_mp3, "gemini")
        except Exception as e:
            if args.tts_provider == "auto" and provider == "elevenlabs" and eleven_key:
                print(f"  ElevenLabs failed ({e}); falling back to Gemini for remaining slides.")
                provider = "gemini"
                synth_one(idx, text, out_mp3, "gemini")
            else:
                raise
        print(f"  audio slide_{idx:03d}.mp3")

    if args.stop_before_video:
        print("Skipping video (--stop-before-video). Done.")
        return
    out_name = pdf.stem + ".mp4"
    out_mp4 = project_dir / out_name
    print("Assembling video (ffmpeg)...")
    assemble_lecture_video(slide_paths, audio_dir, out_mp4)
    print(f"Wrote {out_mp4}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print("Subprocess failed:", e, file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)
