import re
import unicodedata


def normalize_name(value: str) -> str:
    """Lowercase, strip accents and collapse whitespace, to dedupe catalog entries."""
    stripped = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in stripped if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents).strip().lower()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize_name(value)).strip("-")
