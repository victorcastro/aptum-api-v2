from typing import Protocol

from aptum.modules.cv.document import CVDocument


class CVTemplate(Protocol):
    def render(self, doc: CVDocument) -> bytes: ...
