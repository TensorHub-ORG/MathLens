from pathlib import Path
from typing import Protocol

from mathcraft.domain.parsing import DocumentParseResult


class DocumentParser(Protocol):
    def parse(
        self,
        source: Path,
        output_directory: Path,
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> DocumentParseResult: ...
