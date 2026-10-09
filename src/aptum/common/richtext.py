"""Inline rich text for CV free text (summary, descriptions, bullets): a Markdown subset with only
`**bold**`, `*italic*` and `***both***`. `\\*` and `\\\\` are a literal asterisk and backslash.
Anything else (links, lists, headings, HTML) is plain text, and a marker without a partner is
printed as is. Stored and returned as written; renderers and ATS checks go through this module.

Delimiters follow the CommonMark flanking idea, simplified: a run of asterisks opens only when
followed by a non-space and closes only when preceded by one, so `2 * 3 * 4` stays literal."""

import re
from dataclasses import dataclass
from xml.sax.saxutils import escape

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Run:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass
class _Delim:
    index: int  # position in the token list
    count: int  # asterisks left to match
    can_open: bool
    can_close: bool


def _tokenize(text: str) -> list[str | int]:
    """Literal text chunks (str) and asterisk runs (int: their length)."""
    tokens: list[str | int] = []
    buffer: list[str] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text) and text[i + 1] in "*\\":
            buffer.append(text[i + 1])
            i += 2
            continue
        if char == "*":
            end = i
            while end < len(text) and text[end] == "*":
                end += 1
            if buffer:
                tokens.append("".join(buffer))
                buffer = []
            tokens.append(end - i)
            i = end
            continue
        buffer.append(char)
        i += 1
    if buffer:
        tokens.append("".join(buffer))
    return tokens


def _neighbor_char(tokens: list[str | int], index: int, step: int) -> str | None:
    neighbor = index + step
    if 0 <= neighbor < len(tokens) and isinstance(tokens[neighbor], str):
        chunk = tokens[neighbor]
        return chunk[0] if step > 0 else chunk[-1]
    return None


def _compatible(opener: int, closer: int) -> bool:
    return opener == closer or 3 in (opener, closer)


def parse(text: str) -> list[Run]:
    tokens = _tokenize(text)
    # Per token: style changes applied after it (bold, italic) and unmatched asterisks left as text.
    bold_delta = [0] * len(tokens)
    italic_delta = [0] * len(tokens)
    stack: list[_Delim] = []
    delims: dict[int, _Delim] = {}

    for index, token in enumerate(tokens):
        if isinstance(token, str):
            continue
        before, after = _neighbor_char(tokens, index, -1), _neighbor_char(tokens, index, 1)
        delim = _Delim(
            index,
            token if token <= 3 else 0,
            can_open=after is not None and not after.isspace(),
            can_close=before is not None and not before.isspace(),
        )
        delims[index] = delim
        while delim.count and delim.can_close:
            match = next((i for i in range(len(stack) - 1, -1, -1) if _compatible(stack[i].count, delim.count)), None)
            if match is None:
                break
            opener = stack[match]
            del stack[match + 1:]
            taken = min(opener.count, delim.count)
            bold, italic = int(taken >= 2), int(taken != 2)
            bold_delta[opener.index] += bold
            italic_delta[opener.index] += italic
            bold_delta[index] -= bold
            italic_delta[index] -= italic
            opener.count -= taken
            delim.count -= taken
            if not opener.count:
                stack.pop()
        if delim.count and delim.can_open:
            stack.append(delim)

    runs: list[Run] = []
    bold = italic = 0

    def emit(chunk: str) -> None:
        style = (bold > 0, italic > 0)
        if runs and (runs[-1].bold, runs[-1].italic) == style:
            runs[-1] = Run(runs[-1].text + chunk, *style)
        else:
            runs.append(Run(chunk, *style))

    for index, token in enumerate(tokens):
        if isinstance(token, str):
            emit(token)
            continue
        delim = delims[index]
        if bold_delta[index] < 0 or italic_delta[index] < 0:
            bold += min(bold_delta[index], 0)
            italic += min(italic_delta[index], 0)
        leftover = token if token > 3 else delim.count
        if leftover:
            emit("*" * leftover)
        bold += max(bold_delta[index], 0)
        italic += max(italic_delta[index], 0)
    return runs


def to_plain(text: str) -> str:
    """The text without markers, for search, similarity and the ATS checks."""
    return "".join(run.text for run in parse(text))


def _escape_markdown(text: str) -> str:
    return text.replace("\\", "\\\\").replace("*", "\\*")


def to_markdown(runs: list[Run]) -> str:
    parts = []
    for run in runs:
        body = _escape_markdown(run.text)
        marker = "*" * (2 * run.bold + run.italic)
        core = body.strip()
        if not marker or not core:
            parts.append(body)
            continue
        lead = body[: len(body) - len(body.lstrip())]
        trail = body[len(body.rstrip()):]
        parts.append(f"{lead}{marker}{core}{marker}{trail}")
    return "".join(parts)


def to_reportlab(text: str) -> str:
    """Reportlab paragraph markup: escaped text, `<b>`/`<i>` around styled runs, line breaks as `<br/>`."""
    parts = []
    for run in parse(text):
        markup = escape(run.text).replace("\n", "<br/>")
        if run.italic:
            markup = f"<i>{markup}</i>"
        if run.bold:
            markup = f"<b>{markup}</b>"
        parts.append(markup)
    return "".join(parts)


def _slice(runs: list[Run], start: int, end: int) -> list[Run]:
    sliced, offset = [], 0
    for run in runs:
        left, right = max(start, offset), min(end, offset + len(run.text))
        if left < right:
            sliced.append(Run(run.text[left - offset:right - offset], run.bold, run.italic))
        offset += len(run.text)
    return sliced


def split_sentences(text: str) -> list[str]:
    """Sentences (split after `.`, `!` or `?`) each with its own formatting, so a bold span that
    crosses a sentence boundary is closed in every piece."""
    runs = parse(text)
    plain = "".join(run.text for run in runs)
    sentences, start = [], 0
    for match in _SENTENCE_BREAK.finditer(plain):
        sentences.append(to_markdown(_slice(runs, start, match.start())))
        start = match.end()
    sentences.append(to_markdown(_slice(runs, start, len(plain))))
    return sentences
