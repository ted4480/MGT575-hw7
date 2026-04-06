"""Lecture arc from premise + slide descriptions."""

from __future__ import annotations

import json
from typing import Any

from lecture_agents.gemini_client import GeminiClient

ARC_SYSTEM = """You structure lecture flow (acts/phases) for clarity.
Output ONLY valid JSON (no markdown fences).
The arc must be consistent with the premise and the slide descriptions."""


def build_arc_json(
    premise: dict[str, Any],
    slide_description_doc: dict[str, Any],
    client: GeminiClient,
) -> dict[str, Any]:
    user = f"""premise.json:
{json.dumps(premise, ensure_ascii=False, indent=2)}

slide_description.json:
{json.dumps(slide_description_doc, ensure_ascii=False, indent=2)}

Return JSON:
{{
  "flow_summary": string,
  "phases": [
    {{
      "name": string,
      "slide_range": [start_index, end_index] (1-based inclusive),
      "purpose": string,
      "key_ideas": array of strings,
      "transition_to_next": string
    }}
  ],
  "progression_principles": array of strings (how ideas build),
  "callbacks_and_repetition": string (where the lecture circles back, if any)
}}
"""
    data = client.generate_json(ARC_SYSTEM, user)
    if not isinstance(data, dict):
        raise TypeError("arc agent must return a JSON object")
    return data
