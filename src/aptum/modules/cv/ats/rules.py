"""Deterministic generation rules applied to an ATSDocument. They only remove, shorten or
reorder profile content (and fix a years claim to the computed figure); they never add facts."""

import re
from collections.abc import Callable
from datetime import date
from functools import cache
from pathlib import Path

from aptum.modules.cv.ats.document import ATSDocument, ATSExperience
from aptum.modules.cv.ats.report import CVWarning
from aptum.modules.cv.ats.text import normalize_text, similarity
from aptum.modules.cv.ats.years import (
    YEARS_CLAIM,
    YearsOfExperience,
    claim_area,
    true_figure,
)

FILLER_PHRASES_PATH = Path(__file__).parent / "filler_phrases.txt"
MAX_PAGES = 2
RECENT_YEARS = 7
COMPRESSED_MAX_BULLETS = 2
DUPLICATE_THRESHOLD = 0.85
METRIC_SUGGESTION = "Add a metric: users, requests, time saved, cost saved or % improvement."

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "with", "for", "of", "to", "in", "on", "at", "by", "as", "is", "are",
    "was", "were", "be", "our", "we", "you", "your", "their", "this", "that", "team", "teams", "using",
    "will", "who", "can", "into", "from", "all", "other", "new",
})  # fmt: skip


@cache
def filler_phrases(path: Path = FILLER_PHRASES_PATH) -> tuple[str, ...]:
    lines = path.read_text(encoding="utf-8").splitlines()
    phrases = {normalize_text(line) for line in lines if line.strip() and not line.lstrip().startswith("#")}
    return tuple(sorted(phrases, key=len, reverse=True))  # longest first


def has_metric(text: str) -> bool:
    return bool(re.search(r"\d", text))


def meaningful_words(text: str) -> list[str]:
    return [word for word in normalize_text(text).split() if len(word) > 1 and word not in _STOPWORDS]


def _months_ago(value: date, today: date) -> int:
    return (today.year - value.year) * 12 + today.month - value.month


# --- Summary ---------------------------------------------------------------------------------


def apply_summary_rules(doc: ATSDocument, years: YearsOfExperience, warnings: list[CVWarning]) -> None:
    """Years claims in the summary must match the computed figures; a missing summary is built
    only from the headline and the computed years."""
    if not doc.summary:
        if doc.headline and years.total >= 1:
            summary = f"{doc.headline} with {years.total}+ years of professional experience"
            ai_years = years.by_area.get("ai", 0)
            if 1 <= ai_years < years.total:
                summary += f", including {ai_years}+ years in AI"
            doc.summary = summary + "."
        else:
            warnings.append(CVWarning(
                "missing_summary",
                "The profile has no summary, so the CV has none.",
                section="summary",
                suggestion="Add a 2-3 line summary with your role, years of experience and main stack.",
            ))
        return

    def fix(match: re.Match[str]) -> str:
        claimed = int(match.group(1))
        area = claim_area(doc.summary[match.end():])
        figure = true_figure(years, area)
        if claimed <= figure:
            return match.group(0)
        if figure < 1:
            warnings.append(CVWarning(
                "years_unsupported",
                f"The summary claims {claimed} years but the experience dates add up to less than one year.",
                section="summary",
                text=match.group(0),
                suggestion="Add your past roles with their dates, or remove the claim.",
            ))
            return match.group(0)
        warnings.append(CVWarning(
            "years_corrected",
            f"The summary claimed {claimed} years{f' of {area}' if area else ''}; experience dates support {figure}.",
            section="summary",
            text=match.group(0),
            suggestion=f"Use {figure}+ years, computed from your experience dates.",
        ))
        return match.group(0).replace(match.group(1), str(figure), 1)

    doc.summary = YEARS_CLAIM.sub(fix, doc.summary)


# --- Bullets ---------------------------------------------------------------------------------


def remove_filler(doc: ATSDocument, warnings: list[CVWarning]) -> None:
    phrases = filler_phrases()
    for exp in doc.experiences:
        kept: list[str] = []
        for bullet in exp.bullets:
            normalized = normalize_text(bullet)
            phrase = next((p for p in phrases if re.search(rf"(?<!\w){re.escape(p)}(?!\w)", normalized)), None)
            if phrase is None:
                kept.append(bullet)
                continue
            rest = normalized.replace(phrase, " ")
            if len(meaningful_words(rest)) < 3:
                warnings.append(CVWarning(
                    "filler_removed", "Bullet removed: it only contains a filler phrase.",
                    section="experience", item=exp.title, text=bullet,
                    suggestion="Describe what you built or changed and its outcome.",
                ))
                continue
            kept.append(bullet)
            warnings.append(CVWarning(
                "filler_phrase", f"Bullet uses the filler phrase \"{phrase}\".",
                section="experience", item=exp.title, text=bullet,
                suggestion="Start with an action verb (built, led, reduced) and the result.",
            ))
        exp.bullets = kept


def remove_duplicates(doc: ATSDocument, warnings: list[CVWarning], threshold: float = DUPLICATE_THRESHOLD) -> None:
    """Near-duplicate bullets (normalized similarity >= threshold) are kept once, in the most
    recent role (roles are ordered newest first)."""
    seen: list[tuple[str, str]] = []  # (bullet, role title)
    for exp in doc.experiences:
        kept: list[str] = []
        for bullet in exp.bullets:
            original = next(((b, role) for b, role in seen if similarity(b, bullet) >= threshold), None)
            if original is not None:
                warnings.append(CVWarning(
                    "duplicate_removed", f"Bullet removed: near-duplicate of a bullet in \"{original[1]}\".",
                    section="experience", item=exp.title, text=bullet,
                ))
                continue
            kept.append(bullet)
            seen.append((bullet, exp.title))
        exp.bullets = kept


def bullet_score(bullet: str, offer_words: frozenset[str]) -> int:
    """Higher = keep longer: words shared with the offer, plus one for having a metric."""
    return len(set(meaningful_words(bullet)) & offer_words) + int(has_metric(bullet))


def offer_words(offer: str | None) -> frozenset[str]:
    return frozenset(w for w in meaningful_words(offer or "") if len(w) > 2)


def _keep_best(bullets: list[str], keep: int, words: frozenset[str]) -> list[str]:
    ranked = sorted(range(len(bullets)), key=lambda i: (-bullet_score(bullets[i], words), i))
    chosen = sorted(ranked[:keep])
    return [bullets[i] for i in chosen]


def compress_old_roles(
    doc: ATSDocument, today: date, words: frozenset[str], warnings: list[CVWarning]
) -> None:
    """Roles that ended more than RECENT_YEARS ago keep at most COMPRESSED_MAX_BULLETS bullets
    (the most relevant ones) and no description. Recent roles keep full detail."""
    for exp in doc.experiences:
        if exp.end is None or _months_ago(exp.end, today) <= RECENT_YEARS * 12:
            continue
        exp.compressed = True
        if exp.description or len(exp.bullets) > COMPRESSED_MAX_BULLETS:
            warnings.append(CVWarning(
                "role_compressed",
                f"Role ended more than {RECENT_YEARS} years ago: shortened to its "
                f"{COMPRESSED_MAX_BULLETS} most relevant bullets.",
                section="experience", item=exp.title,
            ))
        exp.description = None
        exp.bullets = _keep_best(exp.bullets, COMPRESSED_MAX_BULLETS, words)


# --- Page limit ------------------------------------------------------------------------------


def _drop_weakest(exp: ATSExperience, words: frozenset[str]) -> str:
    index = min(range(len(exp.bullets)), key=lambda i: (bullet_score(exp.bullets[i], words), -i))
    return exp.bullets.pop(index)


def _trim_once(doc: ATSDocument, words: frozenset[str]) -> tuple[str, str] | None:
    """Remove the next least valuable piece: extra bullets of the oldest roles, then old role
    descriptions, then last bullets oldest first, then project descriptions. Roles stay."""
    oldest_first = list(reversed(doc.experiences))
    for exp in oldest_first:
        if len(exp.bullets) > 1:
            return exp.title, _drop_weakest(exp, words)
    for exp in oldest_first:
        if exp.description:
            text, exp.description = exp.description, None
            return exp.title, text
    for exp in oldest_first:
        if exp.bullets:
            return exp.title, _drop_weakest(exp, words)
    for project in reversed(doc.projects):
        if project.description:
            text, project.description = project.description, None
            return project.name, text
    return None


def enforce_page_limit(
    doc: ATSDocument,
    count_pages: Callable[[ATSDocument], int],
    words: frozenset[str],
    warnings: list[CVWarning],
    max_pages: int = MAX_PAGES,
) -> int:
    pages = count_pages(doc)
    while pages > max_pages:
        removed = _trim_once(doc, words)
        if removed is None:
            warnings.append(CVWarning(
                "over_page_limit", f"The CV is {pages} pages even after trimming bullets (limit {max_pages}).",
                suggestion="Shorten the summary or remove old entries in your profile.",
            ))
            break
        item, text = removed
        warnings.append(CVWarning(
            "trimmed_for_length", f"Removed to keep the CV within {max_pages} pages.",
            section="experience", item=item, text=text,
        ))
        pages = count_pages(doc)
    return pages


# --- Warnings only ---------------------------------------------------------------------------


def metric_warnings(doc: ATSDocument, warnings: list[CVWarning]) -> None:
    """Bullets without a number are reported, never given an invented one."""
    for exp in doc.experiences:
        for bullet in exp.bullets:
            if not has_metric(bullet):
                warnings.append(CVWarning(
                    "missing_metric", "Bullet has no number or measurable outcome.",
                    section="experience", item=exp.title, text=bullet, suggestion=METRIC_SUGGESTION,
                ))
