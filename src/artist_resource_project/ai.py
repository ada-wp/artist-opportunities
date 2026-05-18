from __future__ import annotations

import json
import os
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]


class OpenAITextAssistant:
    def __init__(self, model: str = "gpt-5.4-mini") -> None:
        self.model = model
        api_key = os.getenv("OPENAI_API_KEY")
        self.enabled = bool(api_key and OpenAI is not None)
        self._client = OpenAI(api_key=api_key) if self.enabled else None

    def interpret_artist_style(self, profile_text: str) -> str | None:
        prompt = (
            "Summarize the artist's style and thematic signals in 2 short sentences. "
            "Focus on painting-relevant traits."
        )
        return self._generate_text(prompt, profile_text)

    def summarize_opportunity_theme(self, title: str, description: str) -> str | None:
        prompt = (
            "Summarize the opportunity's thematic focus in 1 short sentence for ranking support."
        )
        return self._generate_text(prompt, f"Title: {title}\nDescription: {description}")

    def generate_fit_explanation(self, context: dict[str, Any]) -> str | None:
        prompt = (
            "Write a concise recommendation explanation in 2 sentences. "
            "Mention fit strengths and be cautious about weak assumptions."
        )
        return self._generate_text(prompt, json.dumps(context, ensure_ascii=True))

    def _generate_text(self, instructions: str, content: str) -> str | None:
        if not self.enabled or self._client is None:
            return None

        response = self._client.responses.create(
            model=self.model,
            instructions=instructions,
            input=content,
        )
        return getattr(response, "output_text", None)
