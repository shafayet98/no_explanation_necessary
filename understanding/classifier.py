"""Understanding layer — input classification (Phase 5).

Decides whether user input is a single clean concept or a multi-concept passage.
Heuristics only — no LLM call. The thresholds are intentionally conservative:
every existing eval case (max 121 chars, single clause) must classify as "single".
The canary passage (265 chars, 2 sentences, conjunction-heavy) classifies as "multi".

Internal to the understanding layer; callers go through query.query().
"""

import re

# Coordinating conjunctions and semicolons that signal independent clauses.
_CLAUSE_PATTERN = re.compile(
    r'\b(and|but|or|nor|for|yet|so)\b|;',
    re.IGNORECASE,
)

# Sentence-ending punctuation (not mid-sentence ellipses).
_SENTENCE_SPLIT = re.compile(r'[.!?]+')


def classify(user_input: str) -> str:
    """Return "single" or "multi".

    "multi" requires at least 2 of 3 signals to fire:
      1. character count > 150
      2. sentence count >= 2
      3. coordinating conjunction / semicolon count >= 2
    """
    text = user_input.strip()
    if not text:
        return "single"

    signals = 0

    # Signal 1: raw length
    if len(text) > 150:
        signals += 1

    # Signal 2: sentence count (split on terminal punctuation, ignore empty tokens)
    sentences = [s for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    if len(sentences) >= 2:
        signals += 1

    # Signal 3: independent clause markers
    clause_hits = len(_CLAUSE_PATTERN.findall(text))
    if clause_hits >= 2:
        signals += 1

    return "multi" if signals >= 2 else "single"
