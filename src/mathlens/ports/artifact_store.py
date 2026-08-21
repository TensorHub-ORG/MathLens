from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mathlens.domain.artifacts import PageImageArtifactManifest


@dataclass(frozen=True, slots=True)
class StoredPageArtifact:
    manifest: PageImageArtifactManifest
    directory: Path
    image_path: Path
    manifest_path: Path


class PageArtifactStore(Protocol):
    def publish(
        self,
        manifest: PageImageArtifactManifest,
        content: bytes,
    ) -> StoredPageArtifact: ...
