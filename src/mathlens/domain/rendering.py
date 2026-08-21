from __future__ import annotations

from dataclasses import dataclass

from mathlens.domain.artifacts import CoordinateTransform


@dataclass(frozen=True, slots=True)
class RenderedPage:
    page_number: int
    dpi: int
    pixel_width: int
    pixel_height: int
    png_bytes: bytes
    coordinate_transform: CoordinateTransform
