"""Gemini calls for vision + JSON agents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if m:
        return m.group(1).strip()
    return text


def parse_json_response(text: str) -> Any:
    cleaned = _strip_json_fence(text)
    return json.loads(cleaned)


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate_text(self, system: str, user: str) -> str:
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.4,
        )
        resp = self._client.models.generate_content(
            model=self._model,
            contents=user,
            config=cfg,
        )
        if not resp.text:
            raise RuntimeError("Empty Gemini text response")
        return resp.text

    def generate_json(self, system: str, user: str) -> Any:
        text = self.generate_text(system, user)
        try:
            return parse_json_response(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Model did not return valid JSON: {text[:500]}...") from e

    def generate_json_with_image(
        self, system: str, user_text: str, image_path: Path
    ) -> Any:
        data = image_path.read_bytes()
        parts: list[types.Part] = [
            types.Part.from_bytes(data=data, mime_type="image/png"),
            types.Part.from_text(text=user_text),
        ]
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.35,
        )
        resp = self._client.models.generate_content(
            model=self._model,
            contents=types.Content(role="user", parts=parts),
            config=cfg,
        )
        if not resp.text:
            raise RuntimeError("Empty Gemini vision response")
        try:
            return parse_json_response(resp.text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Model did not return valid JSON for {image_path}: {resp.text[:500]}..."
            ) from e
