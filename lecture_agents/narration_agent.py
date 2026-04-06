"""Per-slide narrations with vision + full context chaining."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lecture_agents.gemini_client import GeminiClient

NARRATION_SYSTEM = """You write spoken lecture narration for a video voiceover.
Output ONLY valid JSON (no markdown fences).
The narration must be plain spoken English: no bullet characters, no stage directions like (pause), no markdown.
Match the instructor voice using style.json and narrator_guidelines_for_tts.
"""


def build_slide_narrations(
    slide_paths: list[Path],
    style: dict[str, Any],
    premise: dict[str, Any],
    arc: dict[str, Any],
    slide_description_doc: dict[str, Any],
    client: GeminiClient,
) -> dict[str, Any]:
    slides_desc = slide_description_doc.get("slides", [])
    combined: list[dict[str, Any]] = []
    prior_narrations: list[dict[str, Any]] = []

    for idx, img in enumerate(slide_paths, start=1):
        this_desc = next((s for s in slides_desc if s.get("slide_index") == idx), None)
        desc_json = json.dumps(this_desc, ensure_ascii=False, indent=2)
        prior_json = json.dumps(
            [{"slide_index": x["slide_index"], "narration": x["narration"]} for x in prior_narrations],
            ensure_ascii=False,
            indent=2,
        )
        title_extra = ""
        if idx == 1:
            title_extra = """
This is the TITLE / opening slide. Requirements:
- The speaker introduces themselves in first person as the course instructor (use a natural name only if provided in style.json or transcript quotes; otherwise say you are the lecture instructor for this generative AI course).
- Give a short, clear overview of what this lecture will cover.
- Keep it welcoming and aligned with title_slide_intro_requirements in style.json if present.
"""
        user = f"""style.json:
{json.dumps(style, ensure_ascii=False, indent=2)}

premise.json:
{json.dumps(premise, ensure_ascii=False, indent=2)}

arc.json:
{json.dumps(arc, ensure_ascii=False, indent=2)}

Current slide description (from slide_description.json):
{desc_json}

Prior slide narrations (JSON array; empty for slide 1):
{prior_json}

Slide index: {idx} of {len(slide_paths)}.
{title_extra}
Write narration the instructor would speak while this slide is on screen.
Length: about 40-120 words for body slides; title slide may be up to ~160 words if needed.
Return JSON: {{"slide_index": {idx}, "narration": string}}
"""
        obj = client.generate_json_with_image(NARRATION_SYSTEM, user, img)
        narration = obj.get("narration", "").strip()
        if not narration:
            raise RuntimeError(f"Empty narration for slide {idx}")
        entry = {
            "slide_index": idx,
            "description": this_desc,
            "narration": narration,
        }
        combined.append(entry)
        prior_narrations.append({"slide_index": idx, "narration": narration})

    return {"slides": combined, "slide_count": len(slide_paths)}
