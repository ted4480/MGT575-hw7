"""Per-slide descriptions with prior-slide chaining."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lecture_agents.gemini_client import GeminiClient

SLIDE_DESC_SYSTEM = """You are a careful teaching assistant watching lecture slides.
You output ONLY valid JSON (no markdown fences).
Describe what a student would see and what instructional role the slide plays.
"""


def describe_slides_chained(
    slide_paths: list[Path],
    client: GeminiClient,
) -> dict[str, Any]:
    slides_out: list[dict[str, Any]] = []
    for idx, img in enumerate(slide_paths, start=1):
        prev = slides_out.copy()
        prev_payload = json.dumps(prev, ensure_ascii=False, indent=2)
        user = f"""Slide index: {idx} of {len(slide_paths)}.

All previous slide descriptions (JSON array; empty on slide 1):
{prev_payload}

Task: describe ONLY the current slide image.
Return JSON object:
{{
  "slide_index": {idx},
  "visible_text_summary": string,
  "layout_and_visuals": string,
  "concepts_emphasized": array of strings,
  "pedagogical_role": string,
  "handoff_to_next_slide": string (what question or idea leads forward; empty on last slide ok)
}}
"""
        obj = client.generate_json_with_image(SLIDE_DESC_SYSTEM, user, img)
        if obj.get("slide_index") != idx:
            obj["slide_index"] = idx
        slides_out.append(obj)
    return {"slides": slides_out, "slide_count": len(slide_paths)}
