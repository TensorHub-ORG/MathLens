from __future__ import annotations

import tempfile
from pathlib import Path

from mathcraft.domain.artifacts import PageImageArtifactManifest
from mathcraft.hashing import sha256_bytes, sha256_file
from mathcraft.ports import StoredPageArtifact


class FileSystemPageArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root.expanduser().resolve()

    def publish(
        self,
        manifest: PageImageArtifactManifest,
        content: bytes,
    ) -> StoredPageArtifact:
        if manifest.content_hash != sha256_bytes(content):
            raise ValueError("content does not match the manifest content hash")

        directory = self._root / manifest.artifact_id[:2] / manifest.artifact_id
        image_path = directory / manifest.page.filename
        manifest_path = directory / "manifest.json"
        if directory.exists():
            return self._load_existing(manifest, directory, image_path, manifest_path)

        directory.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".mathcraft-", dir=directory.parent) as temporary:
            temporary_directory = Path(temporary)
            temporary_image = temporary_directory / manifest.page.filename
            temporary_manifest = temporary_directory / "manifest.json"
            temporary_image.write_bytes(content)
            temporary_manifest.write_text(
                manifest.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
            try:
                temporary_directory.replace(directory)
            except FileExistsError:
                return self._load_existing(manifest, directory, image_path, manifest_path)

        return StoredPageArtifact(
            manifest=manifest,
            directory=directory,
            image_path=image_path,
            manifest_path=manifest_path,
        )

    @staticmethod
    def _load_existing(
        expected: PageImageArtifactManifest,
        directory: Path,
        image_path: Path,
        manifest_path: Path,
    ) -> StoredPageArtifact:
        if not image_path.is_file() or not manifest_path.is_file():
            raise ValueError(f"artifact directory is incomplete: {directory}")
        existing = PageImageArtifactManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        expected_with_original_time = expected.model_copy(
            update={"created_at": existing.created_at}
        )
        if existing != expected_with_original_time:
            raise ValueError(f"artifact manifest conflicts with existing artifact: {directory}")
        if sha256_file(image_path) != existing.content_hash:
            raise ValueError(f"artifact content hash mismatch: {image_path}")
        return StoredPageArtifact(
            manifest=existing,
            directory=directory,
            image_path=image_path,
            manifest_path=manifest_path,
        )
