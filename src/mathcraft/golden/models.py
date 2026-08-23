from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mathcraft.domain import BlockType, BoundingBox, CoordinateSpace, SourceDocument


class ReviewAspect(StrEnum):
    LAYOUT = "layout"
    READING_ORDER = "reading_order"
    TRANSCRIPTION = "transcription"
    FORMULA = "formula"


TRANSCRIBABLE_BLOCK_TYPES = {
    BlockType.TITLE,
    BlockType.TEXT,
    BlockType.TABLE,
    BlockType.PAGE_HEADER,
    BlockType.PAGE_FOOTER,
    BlockType.PAGE_NUMBER,
}


class SuggestionSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    engine: str = Field(min_length=1)
    engine_version: str | None = None
    configuration_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    block_id: str = Field(min_length=1)


class GoldenBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    type: BlockType
    bbox: BoundingBox
    source_transcription: str | None = None
    latex: str | None = None
    notes: str | None = None
    suggested_by: SuggestionSource | None = None
    verified_aspects: tuple[ReviewAspect, ...] = ()

    @model_validator(mode="after")
    def validate_coordinate_space(self) -> GoldenBlock:
        if self.bbox.space is not CoordinateSpace.NORMALIZED:
            raise ValueError("golden block coordinates must use the normalized 0..1000 space")
        if len(self.verified_aspects) != len(set(self.verified_aspects)):
            raise ValueError("block verified aspects must not contain duplicates")
        allowed = (
            {ReviewAspect.FORMULA}
            if self.type is BlockType.FORMULA
            else {ReviewAspect.TRANSCRIPTION}
            if self.type in TRANSCRIBABLE_BLOCK_TYPES
            else set()
        )
        unexpected = set(self.verified_aspects) - allowed
        if unexpected:
            raise ValueError(f"invalid verified aspects for {self.type}: {sorted(unexpected)}")
        if ReviewAspect.FORMULA in self.verified_aspects and not (self.latex or "").strip():
            raise ValueError("verified formula block requires LaTeX")
        if (
            ReviewAspect.TRANSCRIPTION in self.verified_aspects
            and not (self.source_transcription or "").strip()
        ):
            raise ValueError("verified transcription block requires source transcription")
        return self


class GoldenPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    strata: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    verified_aspects: tuple[ReviewAspect, ...] = ()
    image_artifact_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    blocks: tuple[GoldenBlock, ...] = ()
    reading_order: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_blocks_and_reading_order(self) -> GoldenPage:
        block_ids = [block.id for block in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("golden block IDs must be unique within a page")
        if len(self.reading_order) != len(set(self.reading_order)):
            raise ValueError("reading order must not contain duplicate block IDs")
        unknown = set(self.reading_order) - set(block_ids)
        if unknown:
            raise ValueError(f"reading order contains unknown block IDs: {sorted(unknown)}")
        if len(self.verified_aspects) != len(set(self.verified_aspects)):
            raise ValueError("verified aspects must not contain duplicates")
        verified = set(self.verified_aspects)
        content_aspects = verified & {ReviewAspect.TRANSCRIPTION, ReviewAspect.FORMULA}
        if content_aspects:
            raise ValueError("content verification belongs to blocks, not pages")
        dependent = verified - {ReviewAspect.LAYOUT}
        if dependent and ReviewAspect.LAYOUT not in verified:
            raise ValueError("reading order and content verification require verified layout")
        if ReviewAspect.READING_ORDER in verified and set(self.reading_order) != set(block_ids):
            raise ValueError("verified reading order must include every block")
        return self


class GoldenDataset(BaseModel):
    model_config = ConfigDict(frozen=True, serialize_by_alias=True, validate_by_name=True)

    schema_id: Literal["mathcraft.golden-dataset.v3"] = Field(
        default="mathcraft.golden-dataset.v3",
        alias="schema",
    )
    dataset_id: str = Field(min_length=1)
    source: SourceDocument
    source_page_count: int = Field(ge=1)
    render_dpi: int = Field(ge=72, le=1200)
    pages: tuple[GoldenPage, ...] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def migrate_v2_content_verification(cls, value: Any) -> Any:
        if not isinstance(value, dict) or value.get("schema") != "mathcraft.golden-dataset.v2":
            return value
        migrated = dict(value)
        migrated["schema"] = "mathcraft.golden-dataset.v3"
        pages = []
        for raw_page in value.get("pages", []):
            page = dict(raw_page)
            page_aspects = set(page.get("verified_aspects", []))
            blocks = []
            for raw_block in page.get("blocks", []):
                block = dict(raw_block)
                block_aspects = list(block.get("verified_aspects", []))
                if block.get("type") == BlockType.FORMULA and ReviewAspect.FORMULA in page_aspects:
                    block_aspects.append(ReviewAspect.FORMULA)
                elif (
                    block.get("type") in TRANSCRIBABLE_BLOCK_TYPES
                    and ReviewAspect.TRANSCRIPTION in page_aspects
                ):
                    block_aspects.append(ReviewAspect.TRANSCRIPTION)
                block["verified_aspects"] = list(dict.fromkeys(block_aspects))
                blocks.append(block)
            page["blocks"] = blocks
            page["verified_aspects"] = [
                aspect
                for aspect in page.get("verified_aspects", [])
                if aspect in {ReviewAspect.LAYOUT, ReviewAspect.READING_ORDER}
            ]
            pages.append(page)
        migrated["pages"] = pages
        return migrated

    @model_validator(mode="after")
    def validate_pages(self) -> GoldenDataset:
        page_numbers = [page.page_number for page in self.pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("golden page numbers must be unique")
        invalid = [number for number in page_numbers if number > self.source_page_count]
        if invalid:
            raise ValueError(f"golden pages exceed source page count: {invalid}")
        return self
