from pathlib import Path

import pymupdf
import pytest

from mathlens.adapters.pymupdf import PyMuPDFPageRenderer


def _create_pdf(path: Path, page_count: int = 1) -> None:
    document = pymupdf.open()
    for number in range(1, page_count + 1):
        page = document.new_page(width=72, height=144)
        page.insert_text((10, 20), f"Page {number}")
    document.save(path)
    document.close()


def test_renderer_produces_png_with_reversible_coordinate_scale(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_pdf(source)

    rendered = PyMuPDFPageRenderer().render_pages(source, (1,), dpi=144)

    assert len(rendered) == 1
    page = rendered[0]
    assert page.png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert (page.pixel_width, page.pixel_height) == (144, 288)
    assert page.coordinate_transform.scale_x == pytest.approx(2)
    assert page.coordinate_transform.scale_y == pytest.approx(2)


def test_renderer_preserves_requested_page_order(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_pdf(source, page_count=3)

    rendered = PyMuPDFPageRenderer().render_pages(source, (3, 1), dpi=72)

    assert [page.page_number for page in rendered] == [3, 1]


def test_renderer_rejects_page_outside_document(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_pdf(source)

    with pytest.raises(ValueError, match="outside document range"):
        PyMuPDFPageRenderer().render_pages(source, (2,), dpi=300)
