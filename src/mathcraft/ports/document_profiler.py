from pathlib import Path
from typing import Protocol

from mathcraft.domain.profile import DocumentProfile


class DocumentProfiler(Protocol):
    def inspect(self, source: Path, max_pages: int | None = None) -> DocumentProfile: ...
