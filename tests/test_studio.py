from __future__ import annotations

import http.client
import json
import threading
from pathlib import Path

import pymupdf
import pytest

from mathcraft.domain import (
    Block,
    BlockType,
    BoundingBox,
    ContentCandidate,
    CoordinateSpace,
    Document,
    DocumentParseResult,
    Page,
    SourceDocument,
)
from mathcraft.golden import (
    GoldenBlock,
    GoldenDataset,
    GoldenPage,
    ReviewAspect,
    SuggestionSource,
)
from mathcraft.studio import GoldenWorkspace, WorkspaceConflictError
from mathcraft.studio.server import StudioServer

SOURCE_HASH = "a" * 64
ARTIFACT_ID = "b" * 64
CONFIGURATION_HASH = "c" * 64


def normalized_bbox() -> BoundingBox:
    return BoundingBox(
        x0=100,
        y0=200,
        x1=500,
        y1=240,
        space=CoordinateSpace.NORMALIZED,
    )


def write_dataset(path: Path) -> GoldenDataset:
    dataset = GoldenDataset(
        dataset_id="studio-test",
        source=SourceDocument(filename="source.pdf", sha256=SOURCE_HASH),
        source_page_count=1,
        render_dpi=300,
        pages=(
            GoldenPage(
                page_number=1,
                strata=("formula",),
                rationale="exercise the annotation workspace",
                image_artifact_id=ARTIFACT_ID,
            ),
        ),
    )
    path.write_text(dataset.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8")
    return dataset


def write_prediction(path: Path, source_hash: str = SOURCE_HASH) -> None:
    result = DocumentParseResult(
        document=Document(
            id="prediction",
            source_path=Path("source.pdf"),
            source_sha256=source_hash,
            pages=(
                Page(
                    number=1,
                    width=1000,
                    height=1000,
                    coordinate_space=CoordinateSpace.NORMALIZED,
                    blocks=(
                        Block(
                            id="p1-b0",
                            type=BlockType.FORMULA,
                            bbox=normalized_bbox(),
                            candidates=(
                                ContentCandidate(
                                    content=r"x^2+1",
                                    engine="mineru",
                                    engine_version="3.4.5",
                                ),
                            ),
                            selected_candidate=0,
                        ),
                    ),
                ),
            ),
        ),
        engine="mineru",
        engine_version="3.4.5",
        configuration={"method": "ocr"},
        configuration_hash=CONFIGURATION_HASH,
        raw_output_path=Path("content_list_v2.json"),
    )
    path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def create_workspace(tmp_path: Path) -> tuple[GoldenWorkspace, Path]:
    dataset_path = tmp_path / "reference.json"
    prediction_path = tmp_path / "prediction.json"
    artifact_root = tmp_path / "artifacts"
    image_directory = artifact_root / ARTIFACT_ID[:2] / ARTIFACT_ID
    image_directory.mkdir(parents=True)
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 32, 48), False)
    (image_directory / "page.png").write_bytes(pixmap.tobytes("png"))
    write_dataset(dataset_path)
    write_prediction(prediction_path)
    return GoldenWorkspace(dataset_path, artifact_root, (prediction_path,)), dataset_path


def test_workspace_exposes_predictions_and_page_images(tmp_path: Path) -> None:
    workspace, _ = create_workspace(tmp_path)

    snapshot = workspace.snapshot()

    assert snapshot["revision"]
    assert snapshot["image_urls"] == {"1": "/api/images/1"}
    assert snapshot["thumbnail_urls"] == {"1": "/api/thumbnails/1"}
    assert snapshot["prediction_pages"]["1"]["engine_version"] == "3.4.5"
    assert snapshot["prediction_pages"]["1"]["configuration_hash"] == CONFIGURATION_HASH
    assert workspace.image_path(1).read_bytes().startswith(b"\x89PNG")


def test_workspace_saves_valid_page_and_rejects_stale_revision(tmp_path: Path) -> None:
    workspace, dataset_path = create_workspace(tmp_path)
    snapshot = workspace.snapshot()
    page = GoldenPage.model_validate(snapshot["dataset"]["pages"][0])
    block = GoldenBlock(
        id="gold-1",
        type=BlockType.FORMULA,
        bbox=normalized_bbox(),
        latex=r"x^2+1",
        suggested_by=SuggestionSource(
            engine="mineru",
            engine_version="3.4.5",
            block_id="p1-b0",
        ),
    )
    annotated = page.model_copy(
        update={
            "verified_aspects": (ReviewAspect.LAYOUT, ReviewAspect.READING_ORDER),
            "blocks": (block,),
            "reading_order": (block.id,),
        }
    )

    saved = workspace.save_page(annotated, snapshot["revision"])

    persisted = GoldenDataset.model_validate_json(dataset_path.read_bytes())
    assert persisted.pages[0].blocks[0].latex == r"x^2+1"
    assert persisted.pages[0].blocks[0].suggested_by is not None
    assert persisted.pages[0].blocks[0].suggested_by.engine == "mineru"
    assert saved["revision"] != snapshot["revision"]
    with pytest.raises(WorkspaceConflictError, match="reload"):
        workspace.save_page(annotated, snapshot["revision"])


def test_workspace_rejects_prediction_for_another_document(tmp_path: Path) -> None:
    dataset_path = tmp_path / "reference.json"
    prediction_path = tmp_path / "prediction.json"
    write_dataset(dataset_path)
    write_prediction(prediction_path, source_hash="d" * 64)

    with pytest.raises(ValueError, match="different source documents"):
        GoldenWorkspace(dataset_path, tmp_path / "artifacts", (prediction_path,))


def test_studio_server_reads_workspace_image_and_static_assets(tmp_path: Path) -> None:
    workspace, _ = create_workspace(tmp_path)
    static_root = tmp_path / "dist"
    static_root.mkdir()
    (static_root / "index.html").write_text("<main>studio</main>", encoding="utf-8")

    with StudioServer(("127.0.0.1", 0), workspace, static_root) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            connection = http.client.HTTPConnection(*server.server_address)
            connection.request("GET", "/api/workspace")
            response = connection.getresponse()
            snapshot = json.loads(response.read())
            assert response.status == 200
            assert snapshot["dataset"]["dataset_id"] == "studio-test"

            connection.request("GET", "/api/images/1")
            response = connection.getresponse()
            assert response.status == 200
            assert response.read().startswith(b"\x89PNG")

            connection.request("GET", "/api/thumbnails/1")
            response = connection.getresponse()
            assert response.status == 200
            assert response.getheader("Content-Type") == "image/png"
            assert response.read().startswith(b"\x89PNG")

            connection.request("GET", "/missing-client-route")
            response = connection.getresponse()
            assert response.status == 200
            assert "font-src 'self' data:" in response.getheader("Content-Security-Policy", "")
            assert response.read() == b"<main>studio</main>"
        finally:
            server.shutdown()
            thread.join()


def test_studio_server_saves_page_and_reports_conflicts(tmp_path: Path) -> None:
    workspace, _ = create_workspace(tmp_path)
    static_root = tmp_path / "dist"
    static_root.mkdir()
    (static_root / "index.html").write_text("studio", encoding="utf-8")
    snapshot = workspace.snapshot()
    page = snapshot["dataset"]["pages"][0]
    page["verified_aspects"] = []

    with StudioServer(("127.0.0.1", 0), workspace, static_root) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            connection = http.client.HTTPConnection(*server.server_address)
            body = json.dumps({"page": page, "revision": snapshot["revision"]})
            connection.request(
                "PUT",
                "/api/pages/1",
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            saved = json.loads(response.read())
            assert response.status == 200
            assert saved["page"]["verified_aspects"] == []

            connection.request(
                "PUT",
                "/api/pages/1",
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            conflict = json.loads(response.read())
            assert response.status == 409
            assert "reload" in conflict["error"]
        finally:
            server.shutdown()
            thread.join()
