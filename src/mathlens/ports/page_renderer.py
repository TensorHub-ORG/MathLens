from pathlib import Path
from typing import Protocol

from mathlens.domain.rendering import RenderedPage


class PageRenderer(Protocol):
    @property
    def engine(self) -> str: ...

    @property
    def engine_version(self) -> str: ...

    def render_pages(
        self,
        source: Path,
        page_numbers: tuple[int, ...] | None,
        dpi: int,
    ) -> tuple[RenderedPage, ...]: ...
