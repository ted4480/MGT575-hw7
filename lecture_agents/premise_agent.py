"""Lecture premise from full slide descriptions."""

from __future__ import annotations

import json
from typing import Any

from lecture_agents.gemini_client import GeminiClient

PREMISE_SYSTEM = """You design structured learning premises from slide decks.
Output ONLY valid JSON (no markdown fences). Ground claims in the slide descriptions document."""


def build_premise_json(slide_description_doc: dict[str, Any], client: GeminiClient) -> dict[str, Any]:
    doc = json.dumps(slide_description_doc, ensure_ascii=False, indent=2)
    user = f"""Here is slide_description.json (entire document):

{doc}

Return JSON:
{{
  "thesis": string,
  "scope": string,
  "learning_objectives": array of strings,
  "intended_audience": string,
  "key_themes": array of strings,
  "motivation": string (why this lecture exists),
  "constraints_or_assumptions": array of strings
}}
"""
    data = client.generate_json(PREMISE_SYSTEM, user)
    if not isinstance(data, dict):
        raise TypeError("premise agent must return a JSON object")
    return data
