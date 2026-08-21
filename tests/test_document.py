import pytest
from pydantic import ValidationError

from mathlens.domain import BoundingBox, CoordinateSpace


def test_normalized_bounding_box_accepts_valid_coordinates() -> None:
    box = BoundingBox(x0=10, y0=20, x1=900, y1=980, space=CoordinateSpace.NORMALIZED)

    assert box.x1 == 900


def test_bounding_box_rejects_invalid_order() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(x0=10, y0=20, x1=5, y1=980, space=CoordinateSpace.NORMALIZED)
