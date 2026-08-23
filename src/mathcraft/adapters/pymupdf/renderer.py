from __future__ import annotations

from pathlib import Path

import pymupdf

from mathcraft.domain import BoundingBox, CoordinateSpace, CoordinateTransform
from mathcraft.domain.rendering import RenderedPage


class PyMuPDFPageRenderer:
    @property
    def engine(self) -> str:
        return "pymupdf"

    @property
    def engine_version(self) -> str:
        return pymupdf.VersionBind

    def render_pages(
        self,
        source: Path,
        page_numbers: tuple[int, ...] | None,
        dpi: int,
    ) -> tuple[RenderedPage, ...]:
        source = source.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if dpi < 72 or dpi > 1200:
            raise ValueError("dpi must be in the range 72..1200")

        with pymupdf.open(source) as document:  # type: ignore[no-untyped-call]
            selected_pages = page_numbers or tuple(range(1, document.page_count + 1))
            invalid_pages = tuple(
                number for number in selected_pages if number < 1 or number > document.page_count
            )
            if invalid_pages:
                values = ", ".join(str(number) for number in invalid_pages)
                raise ValueError(
                    f"page numbers outside document range 1..{document.page_count}: {values}"
                )

            rendered_pages = []
            for page_number in selected_pages:
                page = document.load_page(page_number - 1)
                pixmap = page.get_pixmap(dpi=dpi, alpha=False)
                bounds = BoundingBox(
                    x0=page.rect.x0,
                    y0=page.rect.y0,
                    x1=page.rect.x1,
                    y1=page.rect.y1,
                    space=CoordinateSpace.PDF_POINT,
                )
                rendered_pages.append(
                    RenderedPage(
                        page_number=page_number,
                        dpi=dpi,
                        pixel_width=pixmap.width,
                        pixel_height=pixmap.height,
                        png_bytes=pixmap.tobytes("png"),
                        coordinate_transform=CoordinateTransform(
                            source_bounds=bounds,
                            scale_x=pixmap.width / page.rect.width,
                            scale_y=pixmap.height / page.rect.height,
                        ),
                    )
                )

            return tuple(rendered_pages)
