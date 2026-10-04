"""Keyword coverage of a job offer, deterministic: which known skills the offer asks for, which
the CV shows, which are missing, and which of the missing ones the profile truthfully supports.
It only suggests; nothing is added to the CV."""

from dataclasses import dataclass, field

from aptum.modules.cv.ats.document import ATSDocument
from aptum.modules.cv.ats.fidelity import profile_text_blocks
from aptum.modules.cv.ats.text import TextIndex
from aptum.modules.profile.models import Profile
from aptum.modules.skills.categories import get_dictionary, skill_key, skill_terms


@dataclass(frozen=True)
class KeywordCoverage:
    offer_keywords: list[str]
    present_in_cv: list[str]
    missing: list[str]
    supported_by_profile: list[str]
    suggestions: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        return round(len(self.present_in_cv) / len(self.offer_keywords), 2) if self.offer_keywords else 1.0


def offer_keywords(offer: str, profile: Profile) -> list[str]:
    """Dictionary skills the offer mentions (name or alias), plus profile skills the dictionary
    does not know. Canonical names, deduplicated, in dictionary order."""
    index = TextIndex(offer)
    found = [entry.name for entry in get_dictionary().entries if index.find_any(entry.terms)]
    known = {skill_key(term) for entry in get_dictionary().entries for term in entry.terms}
    found += [
        ps.skill.name for ps in profile.skills if skill_key(ps.skill.name) not in known and index.find(ps.skill.name)
    ]
    return list(dict.fromkeys(found))


def keyword_coverage(offer: str, doc: ATSDocument, profile: Profile) -> KeywordCoverage:
    keywords = offer_keywords(offer, profile)
    cv = TextIndex(doc.plain_text(skill_labels=False))
    profile_index = TextIndex("\n".join(profile_text_blocks(profile)))
    present = [k for k in keywords if cv.find_any(skill_terms(k))]
    missing = [k for k in keywords if k not in present]
    supported = [k for k in missing if profile_index.find_any(skill_terms(k))]
    suggestions = [
        f"\"{k}\" appears in your profile but not in this CV: move it up in your skills or mention it in a bullet."
        for k in supported
    ]
    suggestions += [
        f"\"{k}\" is requested by the offer and not in your profile: add it only if you have real experience with it."
        for k in missing
        if k not in supported
    ]
    return KeywordCoverage(keywords, present, missing, supported, suggestions)
