from __future__ import annotations

from mathlens.domain import Document, DocumentParseResult
from mathlens.golden import GoldenDataset, ReviewAspect


def prepare_parsing_evaluation(
    reference: GoldenDataset,
    predictions: tuple[DocumentParseResult, ...],
    *,
    verified_only: bool,
) -> tuple[GoldenDataset, Document]:
    if not predictions:
        raise ValueError("at least one parsing prediction is required")

    source_hash = reference.source.sha256
    if any(result.document.source_sha256 != source_hash for result in predictions):
        raise ValueError("golden dataset and prediction source hashes differ")

    pages = tuple(page for result in predictions for page in result.document.pages)
    page_numbers = [page.number for page in pages]
    if len(page_numbers) != len(set(page_numbers)):
        raise ValueError("parsing predictions contain duplicate page numbers")

    predicted_page_numbers = set(page_numbers)
    selected_pages = tuple(
        page for page in reference.pages if page.page_number in predicted_page_numbers
    )
    if verified_only:
        selected_pages = tuple(
            page for page in selected_pages if ReviewAspect.LAYOUT in page.verified_aspects
        )
    if not selected_pages:
        qualifier = " layout-verified" if verified_only else ""
        raise ValueError(f"predictions cover no{qualifier} golden pages")
    selected_reference = reference.model_copy(update={"pages": selected_pages})

    first_document = predictions[0].document
    prediction = first_document.model_copy(
        update={
            "id": f"{first_document.id}-merged",
            "pages": tuple(sorted(pages, key=lambda page: page.number)),
        }
    )
    return selected_reference, prediction
