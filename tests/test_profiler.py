from pathlib import Path

import pymupdf

from mathlens.adapters.pymupdf import PyMuPDFProfiler
from mathlens.domain.profile import PageKind


def test_profiler_detects_vector_page(tmp_path: Path) -> None:
    source = tmp_path / "vector.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "MathLens")
    document.save(source)
    document.close()

    profile = PyMuPDFProfiler().inspect(source)

    assert profile.page_count == 1
    assert profile.inspected_pages[0].kind is PageKind.VECTOR
    assert profile.inspected_pages[0].text_characters == len("MathLens")
