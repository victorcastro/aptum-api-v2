import re
import unicodedata


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_name(value: str) -> str:
    """Lowercase, strip accents and collapse whitespace, to dedupe catalog entries."""
    return re.sub(r"\s+", " ", strip_accents(value)).strip().lower()


def normalize_text(value: str) -> str:
    """Lowercase, no accents, punctuation (except + # . %) as spaces, collapsed whitespace.
    For comparing free text (sentences, titles), not for catalog keys."""
    value = strip_accents(value).lower()
    value = re.sub(r"[^\w+#.%]+", " ", value)
    return re.sub(r"\s+", " ", value).strip(" .")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize_name(value)).strip("-")
