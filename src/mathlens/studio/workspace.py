from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

import pymupdf
from pydantic import ValidationError

from mathlens.domain import DocumentParseResult
from mathlens.golden import GoldenDataset, GoldenPage
from mathlens.hashing import sha256_bytes


class WorkspaceConflictError(RuntimeError):
    """Raised when a save would overwrite a newer dataset revision."""


class GoldenWorkspace:
    """Validated, concurrency-safe access to one local golden dataset."""

    def __init__(
        self,
        dataset_path: Path,
        artifact_root: Path,
        prediction_paths: tuple[Path, ...] = (),
    ) -> None:
        self._dataset_path = dataset_path.expanduser().resolve()
        self._artifact_root = artifact_root.expanduser().resolve()
        self._lock = threading.Lock()
        self._thumbnail_lock = threading.Lock()
        self._thumbnail_cache: dict[int, bytes] = {}
        self._predictions = self._load_predictions(prediction_paths)
        dataset, _ = self._read_dataset()
        self._validate_predictions(dataset)

    def snapshot(self) -> dict[str, Any]:
        dataset, revision = self._read_dataset()
        prediction_pages: dict[str, dict[str, Any]] = {}
        for result in self._predictions:
            for page in result.document.pages:
                prediction_pages[str(page.number)] = {
                    "engine": result.engine,
                    "engine_version": result.engine_version,
                    "configuration_hash": result.configuration_hash,
                    "blocks": [block.model_dump(mode="json") for block in page.blocks],
                }
        return {
            "dataset": dataset.model_dump(mode="json", by_alias=True),
            "revision": revision,
            "prediction_pages": prediction_pages,
            "image_urls": {
                str(page.page_number): f"/api/images/{page.page_number}"
                for page in dataset.pages
                if page.image_artifact_id is not None
            },
            "thumbnail_urls": {
                str(page.page_number): f"/api/thumbnails/{page.page_number}"
                for page in dataset.pages
                if page.image_artifact_id is not None
            },
        }

    def save_page(self, page: GoldenPage, expected_revision: str) -> dict[str, Any]:
        with self._lock:
            dataset, revision = self._read_dataset()
            if revision != expected_revision:
                raise WorkspaceConflictError("golden dataset changed on disk; reload before saving")
            page_index = next(
                (
                    index
                    for index, existing in enumerate(dataset.pages)
                    if existing.page_number == page.page_number
                ),
                None,
            )
            if page_index is None:
                raise ValueError(f"page {page.page_number} is not selected in this dataset")
            pages = list(dataset.pages)
            pages[page_index] = page
            updated = dataset.model_copy(update={"pages": tuple(pages)})
            payload = (updated.model_dump_json(indent=2, by_alias=True) + "\n").encode()
            self._atomic_write(payload)
            return {
                "page": page.model_dump(mode="json"),
                "revision": sha256_bytes(payload),
            }

    def image_path(self, page_number: int) -> Path:
        dataset, _ = self._read_dataset()
        page = next(
            (candidate for candidate in dataset.pages if candidate.page_number == page_number),
            None,
        )
        if page is None or page.image_artifact_id is None:
            raise FileNotFoundError(f"page {page_number} has no image artifact")
        artifact_id = page.image_artifact_id
        image_path = self._artifact_root / artifact_id[:2] / artifact_id / "page.png"
        if not image_path.is_file():
            raise FileNotFoundError(f"page image artifact is missing: {image_path}")
        return image_path

    def thumbnail_bytes(self, page_number: int) -> bytes:
        cached = self._thumbnail_cache.get(page_number)
        if cached is not None:
            return cached
        with self._thumbnail_lock:
            cached = self._thumbnail_cache.get(page_number)
            if cached is not None:
                return cached
            pixmap = pymupdf.Pixmap(  # type: ignore[no-untyped-call]
                str(self.image_path(page_number))
            )
            shrink = 0
            while pixmap.width // (2 ** (shrink + 1)) >= 240:
                shrink += 1
            if shrink:
                pixmap.shrink(shrink)  # type: ignore[no-untyped-call]
            thumbnail: bytes = pixmap.tobytes("png")  # type: ignore[no-untyped-call]
            self._thumbnail_cache[page_number] = thumbnail
            return thumbnail

    def _read_dataset(self) -> tuple[GoldenDataset, str]:
        payload = self._dataset_path.read_bytes()
        try:
            dataset = GoldenDataset.model_validate_json(payload)
        except (ValidationError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid golden dataset: {error}") from error
        return dataset, sha256_bytes(payload)

    def _load_predictions(
        self, prediction_paths: tuple[Path, ...]
    ) -> tuple[DocumentParseResult, ...]:
        predictions = []
        seen_pages: set[int] = set()
        for path in prediction_paths:
            resolved = path.expanduser().resolve()
            try:
                prediction = DocumentParseResult.model_validate_json(resolved.read_bytes())
            except (ValidationError, json.JSONDecodeError) as error:
                raise ValueError(f"invalid parser prediction {resolved}: {error}") from error
            pages = {page.number for page in prediction.document.pages}
            overlap = seen_pages & pages
            if overlap:
                raise ValueError(f"multiple predictions provided for pages: {sorted(overlap)}")
            seen_pages.update(pages)
            predictions.append(prediction)
        return tuple(predictions)

    def _validate_predictions(self, dataset: GoldenDataset) -> None:
        selected_pages = {page.page_number for page in dataset.pages}
        for prediction in self._predictions:
            if prediction.document.source_sha256 != dataset.source.sha256:
                raise ValueError(
                    "prediction and golden dataset refer to different source documents"
                )
            unknown = {page.number for page in prediction.document.pages} - selected_pages
            if unknown:
                raise ValueError(f"prediction contains unselected pages: {sorted(unknown)}")

    def _atomic_write(self, payload: bytes) -> None:
        self._dataset_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=self._dataset_path.parent,
                prefix=f".{self._dataset_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            temporary_path.replace(self._dataset_path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
