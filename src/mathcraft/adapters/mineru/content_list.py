from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mathcraft.domain import (
    Block,
    BlockType,
    BoundingBox,
    ContentCandidate,
    CoordinateSpace,
    DiagnosticLevel,
    Document,
    DocumentParseResult,
    Page,
    ParseDiagnostic,
)
from mathcraft.hashing import sha256_bytes, sha256_file

_TYPE_MAP = {
    "title": BlockType.TITLE,
    "paragraph": BlockType.TEXT,
    "list": BlockType.TEXT,
    "index": BlockType.TEXT,
    "code": BlockType.TEXT,
    "algorithm": BlockType.TEXT,
    "page_aside_text": BlockType.TEXT,
    "page_footnote": BlockType.TEXT,
    "equation_interline": BlockType.FORMULA,
    "image": BlockType.FIGURE,
    "chart": BlockType.FIGURE,
    "table": BlockType.TABLE,
    "page_header": BlockType.PAGE_HEADER,
    "page_footer": BlockType.PAGE_FOOTER,
    "page_number": BlockType.PAGE_NUMBER,
}

_CONTENT_KEYS = {
    "title": ("title_content",),
    "paragraph": ("paragraph_content",),
    "equation_interline": ("math_content",),
    "image": ("image_caption", "image_footnote"),
    "chart": ("chart_content", "chart_caption", "chart_footnote"),
    "table": ("table_caption", "table_body", "table_footnote"),
    "code": ("code_content", "code_caption", "code_footnote"),
    "algorithm": ("algorithm_content", "algorithm_caption", "algorithm_footnote"),
    "list": ("list_items",),
    "index": ("list_items",),
    "page_header": ("page_header_content",),
    "page_footer": ("page_footer_content",),
    "page_number": ("page_number_content",),
    "page_aside_text": ("page_aside_text_content",),
    "page_footnote": ("page_footnote_content",),
}


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_flatten_text(item) for item in value)
    if isinstance(value, dict):
        direct_content = value.get("content")
        if isinstance(direct_content, str):
            return direct_content
        return "".join(_flatten_text(item) for item in value.values())
    return ""


def _extract_content(item_type: str, content: dict[str, Any]) -> str:
    values = [content[key] for key in _CONTENT_KEYS.get(item_type, ()) if key in content]
    return "\n".join(part for value in values if (part := _flatten_text(value)))


def _parse_bbox(value: object) -> BoundingBox | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    if not all(isinstance(coordinate, int | float) for coordinate in value):
        return None
    x0, y0, x1, y1 = (float(coordinate) for coordinate in value)
    try:
        return BoundingBox(
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            space=CoordinateSpace.NORMALIZED,
        )
    except ValueError:
        return None


def import_content_list_v2(
    content_list_path: Path,
    source: Path,
    engine_version: str,
    start_page: int = 1,
    configuration: dict[str, str] | None = None,
) -> DocumentParseResult:
    content_list_path = content_list_path.expanduser().resolve()
    source = source.expanduser().resolve()
    if start_page < 1:
        raise ValueError("start_page must be at least 1")
    raw = json.loads(content_list_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or any(not isinstance(page, list) for page in raw):
        raise ValueError("MinerU content_list_v2 must be a list of page item lists")

    diagnostics = []
    pages = []
    for page_offset, raw_page in enumerate(raw):
        page_number = start_page + page_offset
        blocks = []
        for item_index, raw_item in enumerate(raw_page):
            if not isinstance(raw_item, dict):
                raise ValueError(f"MinerU page {page_number} item {item_index} must be an object")
            bbox = _parse_bbox(raw_item.get("bbox"))
            if bbox is None:
                diagnostics.append(
                    ParseDiagnostic(
                        level=DiagnosticLevel.WARNING,
                        code="mineru.missing_or_invalid_bbox",
                        message="Item omitted because it has no valid normalized bounding box.",
                        page_number=page_number,
                        item_index=item_index,
                    )
                )
                continue
            item_type = raw_item.get("type")
            if not isinstance(item_type, str):
                raise ValueError(f"MinerU page {page_number} item {item_index} has no string type")
            raw_content = raw_item.get("content", {})
            if not isinstance(raw_content, dict):
                raise ValueError(
                    f"MinerU page {page_number} item {item_index} content must be an object"
                )
            content = _extract_content(item_type, raw_content)
            candidates = (
                (
                    ContentCandidate(
                        content=content,
                        engine="mineru",
                        engine_version=engine_version,
                    ),
                )
                if content
                else ()
            )
            blocks.append(
                Block(
                    id=f"p{page_number}-b{item_index}",
                    type=_TYPE_MAP.get(item_type, BlockType.UNKNOWN),
                    bbox=bbox,
                    candidates=candidates,
                    selected_candidate=0 if candidates else None,
                )
            )
        pages.append(
            Page(
                number=page_number,
                width=1000,
                height=1000,
                coordinate_space=CoordinateSpace.NORMALIZED,
                blocks=tuple(blocks),
            )
        )

    source_hash = sha256_file(source)
    configuration = configuration or {"source": "content_list_v2_import"}
    serialized_configuration = json.dumps(
        configuration,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    configuration_hash = sha256_bytes(serialized_configuration)
    raw_output_hash = sha256_file(content_list_path)
    document_id = sha256_bytes(
        f"mineru\0{engine_version}\0{source_hash}\0{raw_output_hash}\0{start_page}".encode()
    )
    return DocumentParseResult(
        document=Document(
            id=document_id,
            source_path=source,
            source_sha256=source_hash,
            pages=tuple(pages),
            metadata={
                "engine": "mineru",
                "engine_version": engine_version,
                "configuration_hash": configuration_hash,
                "raw_output_sha256": raw_output_hash,
            },
        ),
        engine="mineru",
        engine_version=engine_version,
        configuration=configuration,
        configuration_hash=configuration_hash,
        raw_output_path=content_list_path,
        diagnostics=tuple(diagnostics),
    )
