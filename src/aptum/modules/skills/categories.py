"""Skill name aliases backed by `data/skill_dictionary.json`.

A skill name is normalized and looked up as a whole (name or alias) to recognize it in free
text (job offers, CVs). It does not decide a skill's CV category: that is the user's choice
(`profile_skills.category_id`), `Other` by default.
"""

import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from aptum.common.utils import normalize_name

DICTIONARY_PATH = Path(__file__).parent / "data" / "skill_dictionary.json"


def skill_key(name: str) -> str:
    """Case/accent-insensitive lookup key; `-`, `_` and `/` count as spaces ("CI/CD" == "ci cd").
    A leading dot is kept (".NET" is not "net"); trailing punctuation is dropped."""
    return re.sub(r"[\s\-_/]+", " ", normalize_name(name)).strip(" ,;:").rstrip(".")


@dataclass(frozen=True)
class DictionaryEntry:
    name: str
    terms: tuple[str, ...]  # name + aliases, as written in the dictionary


@dataclass(frozen=True)
class SkillDictionary:
    version: int
    entries: tuple[DictionaryEntry, ...]
    by_key: dict[str, DictionaryEntry]


def load_dictionary(path: Path = DICTIONARY_PATH) -> SkillDictionary:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries: list[DictionaryEntry] = []
    by_key: dict[str, DictionaryEntry] = {}
    for items in raw["categories"].values():  # the category keys only group the file for reading
        for item in items:
            entry = DictionaryEntry(item["name"], (item["name"], *item.get("aliases", ())))
            entries.append(entry)
            for term in entry.terms:
                key = skill_key(term)
                if key in by_key and by_key[key] is not entry:
                    raise ValueError(f"Skill dictionary: '{term}' is listed twice")
                by_key[key] = entry
    return SkillDictionary(int(raw["version"]), tuple(entries), by_key)


@cache
def get_dictionary() -> SkillDictionary:
    return load_dictionary()


def lookup(name: str) -> DictionaryEntry | None:
    return get_dictionary().by_key.get(skill_key(name))


def skill_terms(name: str) -> tuple[str, ...]:
    """The name plus every alias of its dictionary entry, to recognize the skill in free text."""
    entry = lookup(name)
    return tuple(dict.fromkeys((name, *(entry.terms if entry else ()))))
