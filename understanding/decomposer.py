"""Understanding layer — LLM concept decomposition (Phase 5).

Takes a multi-concept passage and extracts 2–4 distinct emotional/sensory/conceptual
moments as (label, clean_query) pairs. Each clean_query is a concise rephrasing
suitable for the vector search + rerank pipeline.

Uses claude-haiku-4-5-20251001 via the Anthropic SDK. Lazy-loads the client on first
call. Raises RuntimeError if ANTHROPIC_API_KEY is not set.

Internal to the understanding layer; callers go through query.query().
"""

from __future__ import annotations

import json
import os

_client = None

_SYSTEM_PROMPT = """\
You are a concept extractor for a reverse dictionary system. A reverse dictionary maps
a description or feeling to the single English word that names it (e.g. "the smell of
rain on dry earth" → petrichor; "deep longing for home" → nostalgia).

Given a passage of text, identify 2 to 4 distinct emotions, feelings, states of mind,
or named sensory experiences. For each, produce:
- "label": a short 2–5 word phrase describing what the concept IS (not what happens
  in the passage)
- "query": a concise 5–12 word description of that feeling or experience written as
  a dictionary lookup — plain language, no metaphors, no first-person pronouns.
  Think: "what would someone type to find the word for this feeling?"

Return ONLY a JSON array with no surrounding text. Example format:
[
  {"label": "the rain smell", "query": "smell of rain on dry earth"},
  {"label": "calm acceptance", "query": "peaceful acceptance of what cannot be changed"}
]

Rules:
- 2 to 4 items maximum — prefer fewer, more distinct concepts over many overlapping ones.
- Focus on feelings, emotions, or named human experiences — not physical actions.
- Each query must stand alone as a complete dictionary lookup phrase.
- Do not repeat the same concept twice with different wording.
- Return valid JSON only.
"""


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Set it in the environment or in a .env file to enable multi-concept decomposition."
            )
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _parse_response(text: str) -> list[tuple[str, str]]:
    """Parse LLM JSON response into (label, query) tuples. Raises ValueError on bad output."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    data = json.loads(text)
    if not isinstance(data, list) or not data:
        raise ValueError(f"Expected a non-empty JSON array, got: {text!r}")
    result = []
    for item in data:
        label = str(item.get("label", "")).strip()
        query = str(item.get("query", "")).strip()
        if not label or not query:
            raise ValueError(f"Item missing label or query: {item!r}")
        result.append((label, query))
    return result


def decompose(text: str) -> list[tuple[str, str]]:
    """Extract 2–4 (label, clean_query) pairs from a multi-concept passage.

    Raises RuntimeError if ANTHROPIC_API_KEY is not set.
    Falls back on parse failure by retrying once with an explicit reminder, then
    raises ValueError if the second attempt also fails.
    """
    client = _get_client()

    def _call() -> str:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )
        return message.content[0].text

    raw = _call()
    try:
        return _parse_response(raw)
    except (json.JSONDecodeError, ValueError):
        # One retry with an explicit JSON reminder
        retry_raw = _call()
        return _parse_response(retry_raw)
