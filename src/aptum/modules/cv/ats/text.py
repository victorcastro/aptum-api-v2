"""Deterministic text helpers shared by the ATS pipeline: normalization, term search, similarity."""

import re
import unicodedata
from difflib import SequenceMatcher
from functools import cache

from aptum.modules.skills.categories import skill_key

# Dictionary terms that are also everyday English words. They only count as a match when the
# occurrence is written with a capital letter ("REST", "Go", "Swift"), not in "the rest of", "go live".
AMBIGUOUS_TERMS = frozenset({
    "go", "rest", "git", "compose", "lambda", "spring", "express", "combine", "agents", "monitoring",
    "containers", "nest", "node", "rails", "solid", "chroma", "oracle", "swift", "rust", "ruby",
    "ml", "dl", "js", "ts", "eda", "iac", "cdk", "dart", "expo", "flask", "jest", "claude", "gpt",
    "bash", "helm", "serverless", "evals", "prompting", "lora", "torch", "keras", "laravel",
})  # fmt: skip


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_text(value: str) -> str:
    """Lowercase, no accents, punctuation (except + # .) as spaces, collapsed whitespace."""
    value = strip_accents(value).lower()
    value = re.sub(r"[^\w+#.%]+", " ", value)
    return re.sub(r"\s+", " ", value).strip(" .")


@cache
def _term_regex(term: str) -> re.Pattern[str]:
    tokens = [re.escape(token) for token in skill_key(term).split(" ") if token]
    body = r"[\s\-_/]+".join(tokens)
    return re.compile(rf"(?<![a-z0-9]){body}(?![a-z0-9])", re.IGNORECASE)


class TextIndex:
    """A piece of text prepared for repeated term lookups."""

    def __init__(self, text: str) -> None:
        self.original = strip_accents(text)

    def find(self, term: str) -> bool:
        if not skill_key(term):
            return False
        ambiguous = skill_key(term) in AMBIGUOUS_TERMS
        for match in _term_regex(term).finditer(self.original):
            if not ambiguous or any(c.isupper() for c in match.group(0)):
                return True
        return False

    def find_any(self, terms: tuple[str, ...] | list[str]) -> bool:
        return any(self.find(term) for term in terms)


def similarity(a: str, b: str) -> float:
    """0..1 similarity of two sentences after normalization (order-aware, typo tolerant)."""
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()
