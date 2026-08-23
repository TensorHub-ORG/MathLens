from __future__ import annotations

from pathlib import Path

import pymupdf

from mathcraft.domain.profile import DocumentProfile, PageKind, PageProfile
from mathcraft.hashing import sha256_file


def _classify_page(text_characters: int, images: int, drawings: int) -> PageKind:
    has_text = text_characters > 0
    has_visual_content = images > 0 or drawings > 0
    if has_text and has_visual_content:
        return PageKind.MIXED
    if has_text:
        return PageKind.VECTOR
    if has_visual_content:
        return PageKind.SCANNED
    return PageKind.EMPTY


class PyMuPDFProfiler:
    def inspect(self, source: Path, max_pages: int | None = None) -> DocumentProfile:
        source = source.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be at least 1")

        # PyMuPDF exposes this constructor dynamically, so its package typing is incomplete.
        with pymupdf.open(source) as document:  # type: ignore[no-untyped-call]
            inspected_count = document.page_count
            if max_pages is not None:
                inspected_count = min(max_pages, document.page_count)

            pages = []
            for page_index in range(inspected_count):
                page = document.load_page(page_index)
                text_characters = len(page.get_text("text").strip())
                image_count = len(page.get_images(full=True))
                drawing_count = len(page.get_drawings())
                pages.append(
                    PageProfile(
                        number=page_index + 1,
                        width_points=page.rect.width,
                        height_points=page.rect.height,
                        text_characters=text_characters,
                        images=image_count,
                        drawings=drawing_count,
                        kind=_classify_page(text_characters, image_count, drawing_count),
                    )
                )

            return DocumentProfile(
                source_path=source,
                source_sha256=sha256_file(source),
                file_size_bytes=source.stat().st_size,
                page_count=document.page_count,
                inspected_pages=tuple(pages),
            )
