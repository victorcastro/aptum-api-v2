"""What the ATS pipeline reports back besides the PDF. Never rendered inside the PDF."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CVWarning:
    code: str
    message: str
    section: str | None = None
    item: str | None = None
    text: str | None = None
    suggestion: str | None = None
