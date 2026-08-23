from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mathcraft.domain.document import BoundingBox, CoordinateSpace


class CoordinateTransform(BaseModel):
    """Invertible axis-aligned mapping from displayed PDF points to image pixels."""

    model_config = ConfigDict(frozen=True)

    source_space: Literal[CoordinateSpace.PDF_POINT] = CoordinateSpace.PDF_POINT
    target_space: Literal[CoordinateSpace.PIXEL] = CoordinateSpace.PIXEL
    source_bounds: BoundingBox
    scale_x: float = Field(gt=0)
    scale_y: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_source_bounds(self) -> CoordinateTransform:
        if self.source_bounds.space is not CoordinateSpace.PDF_POINT:
            raise ValueError("source bounds must use PDF point coordinates")
        return self

    def pdf_point_to_pixel(self, x: float, y: float) -> tuple[float, float]:
        return (
            (x - self.source_bounds.x0) * self.scale_x,
            (y - self.source_bounds.y0) * self.scale_y,
        )

    def pixel_to_pdf_point(self, x: float, y: float) -> tuple[float, float]:
        return (
            x / self.scale_x + self.source_bounds.x0,
            y / self.scale_y + self.source_bounds.y0,
        )


class PageImageMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    dpi: int = Field(ge=72, le=1200)
    pixel_width: int = Field(gt=0)
    pixel_height: int = Field(gt=0)
    media_type: Literal["image/png"] = "image/png"
    filename: Literal["page.png"] = "page.png"
    coordinate_transform: CoordinateTransform


class SourceDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    filename: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PageImageArtifactManifest(BaseModel):
    model_config = ConfigDict(frozen=True, serialize_by_alias=True, validate_by_name=True)

    schema_id: Literal["mathcraft.page-image.v1"] = Field(
        default="mathcraft.page-image.v1",
        alias="schema",
    )
    artifact_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    parents: tuple[str, ...] = ()
    stage: Literal["page_render"] = "page_render"
    engine: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    source: SourceDocument
    page: PageImageMetadata
    diagnostics: tuple[str, ...] = ()
