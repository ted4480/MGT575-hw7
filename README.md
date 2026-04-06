# Homework 7: Agentic Video Lecture Pipeline

Python pipeline: **PDF slide deck → structured JSON agents → per-slide MP3 → one narrated MP4 (ffmpeg)**. Speaking style is derived from `Input/instructor_lecture_transcript.txt` and stored in `style.json` for the narration agent.

**Default TTS** is **Gemini** (`gemini-2.5-flash-preview-tts`), with `narrator_guidelines_for_tts` from `style.json` passed into the speech prompt. **ElevenLabs** is optional (`--tts-provider elevenlabs` or `auto` to try ElevenLabs first). **ffmpeg** is required as soon as you run the audio step (MP3 encoding for Gemini TTS, chunk merging, and final video).

## Repository layout

- `run_lecture_pipeline.py` — entrypoint
- `lecture_agents/` — agents, PDF rasterization, TTS, video assembly
- `Lecture_17_AI_screenplays.pdf` — lecture deck (grader runs against this)
- `Input/instructor_lecture_transcript.txt` — instructor captions/transcript for the **style agent** (do not remove; replace with your real transcript if the course provides one)
- `projects/project_YYYYMMDD_HHMMSS/` — each run writes PNGs, JSON, audio, and the final MP4 here (media is gitignored)

## Prerequisites

1. **Python 3.11+** (3.14 tested)
2. **ffmpeg** on your PATH (e.g. macOS: `brew install ffmpeg`)
3. **API keys** in a local RTF file (not committed). By default the script looks for `API_Key.rtf` in the parent folder of this repo (e.g. `Gen AI/API_Key.rtf` next to `HW 7/`), matching the course layout. Required entries:
   - `React Gemini API Key = ...` — Gemini for all LLM/vision steps and (by default) TTS
   - `ElevenLabs_API_Key = ...` — only if you use `--tts-provider elevenlabs` or `auto`

No `.env` file is used (per assignment). Pass a different path with `--keys-file` if needed.

## Setup

```bash
cd "/path/to/HW 7"
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the full pipeline

```bash
source .venv/bin/activate
python run_lecture_pipeline.py
```

Options:

- `--keys-file /absolute/path/API_Key.rtf` — override key file location
- `--skip-style` — reuse existing `style.json` at repo root
- `--stop-before-audio` — stop after `slide_description_narration.json` (no TTS/video)
- `--stop-before-video` — create `audio/slide_NNN.mp3` but skip final mux/concat
- `--tts-provider gemini|elevenlabs|auto` — default `gemini`
- `--gemini-tts-voice <name>` — Gemini prebuilt voice (default `Kore`)
- `--elevenlabs-voice-id <id>` — override default ElevenLabs voice

Outputs:

- `style.json` (repo root)
- `projects/project_<timestamp>/slide_images/slide_XXX.png`
- `projects/project_<timestamp>/slide_description.json`
- `projects/project_<timestamp>/premise.json`
- `projects/project_<timestamp>/arc.json`
- `projects/project_<timestamp>/slide_description_narration.json`
- `projects/project_<timestamp>/audio/slide_XXX.mp3`
- `projects/project_<timestamp>/Lecture_17_AI_screenplays.mp4`

## Five Cursor prompts (suggested workflow)

Use these in order when building or debugging the assignment in Cursor:

1. **Scaffold & contracts** — “Create repo layout per HW7: `run_lecture_pipeline.py`, `lecture_agents/` package, `requirements.txt`, `.gitignore` (exclude PNG/MP3/MP4), `projects/`, README. Add `Input/instructor_lecture_transcript.txt` as the style source. Document keys via `--keys-file` pointing at `Gen AI/API_Key.rtf`, no `.env`.”

2. **Style + PDF + slide description agent** — “Implement style agent: read full transcript, call Gemini, write `style.json`. Rasterize `Lecture_17_AI_screenplays.pdf` with PyMuPDF to `slide_images/slide_XXX.png`. Implement slide description agent: for each slide, send current PNG + JSON array of all prior descriptions; write `slide_description.json`.”

3. **Premise + arc agents** — “Implement premise agent consuming entire `slide_description.json`. Implement arc agent consuming `premise.json` + `slide_description.json`. Both emit structured JSON only.”

4. **Narration agent** — “For each slide, call Gemini with image + `style.json` + `premise.json` + `arc.json` + full `slide_description.json` + prior narrations only. Title slide: self-intro + topic overview. Write `slide_description_narration.json` with description + narration per slide.”

5. **TTS + ffmpeg** — “Implement Gemini TTS (preview model) with style-aware prompts; chunk long narrations; WAV → MP3 via ffmpeg. Optionally support ElevenLabs. Per slide mux PNG+MP3 with `-shortest`, concat segments into `<pdf_basename>.mp4`. Require ffmpeg before audio.”

## Grading / GitHub submission

Do **not** commit images, audio, or video. JSON artifacts under `projects/project_*/` **should** be committed so the grader can inspect agent outputs. Keep `API_Key.rtf` out of the repo.

## Note on `instructor_lecture_transcript.txt`

If your instructor provides an official caption file, replace the contents of `Input/instructor_lecture_transcript.txt` with that source so `style.json` reflects the real lecture voice. The bundled file is a **synthetic transcript** aligned with Lecture 17 (agentic screenplays) so the pipeline runs end-to-end before official captions are available.
