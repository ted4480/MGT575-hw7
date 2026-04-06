"""Build style.json from instructor transcript (grounded in that file)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lecture_agents.gemini_client import GeminiClient

STYLE_SYSTEM = """You are an expert in sociolinguistics and instructional design.
You analyze lecture transcripts and output ONLY valid JSON (no markdown fences).
Ground every claim in the transcript text; prefer short verbatim snippets in example_quotes_from_transcript.
"""


def build_style_json(transcript_path: Path, client: GeminiClient) -> dict[str, Any]:
    transcript = transcript_path.read_text(encoding="utf-8")
    user = f"""The following file is an instructor lecture transcript (full text):

---BEGIN TRANSCRIPT---
{transcript}
---END TRANSCRIPT---

Return a JSON object with these keys (you may add optional keys if helpful):
- source_file: string (basename of the transcript file)
- tone: string (e.g., conversational, academic, encouraging)
- pacing: string (how ideas are rolled out; reference evidence from transcript)
- fillers_and_discourse_markers: array of strings (e.g., "um", "okay?", "so", "right?")
- how_ideas_are_framed: string (signposting, repetition, "big picture" moments)
- rhetorical_moves: array of strings (e.g., "restates thesis", "checks engagement")
- vocabulary_register: string (technical vs plain language balance)
- teaching_tics: array of strings (habitual phrases the speaker uses)
- example_quotes_from_transcript: array of 3-6 short strings copied or lightly trimmed from the transcript
- narrator_guidelines_for_tts: array of concrete bullet strings telling a narrator how to sound like this instructor
- title_slide_intro_requirements: string — how slide 1 should introduce the speaker and preview the topic, consistent with this voice

The JSON must be valid UTF-8 and parseable by json.loads.
"""
    data = client.generate_json(STYLE_SYSTEM, user)
    if not isinstance(data, dict):
        raise TypeError("style agent must return a JSON object")
    data["source_file"] = transcript_path.name
    return data
