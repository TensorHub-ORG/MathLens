from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from mathlens.golden import GoldenPage
from mathlens.studio.workspace import GoldenWorkspace, WorkspaceConflictError

MAX_REQUEST_BYTES = 8 * 1024 * 1024


class StudioServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        workspace: GoldenWorkspace,
        static_root: Path,
    ) -> None:
        self.workspace = workspace
        self.static_root = static_root.expanduser().resolve()
        super().__init__(address, StudioRequestHandler)


class StudioRequestHandler(BaseHTTPRequestHandler):
    server: StudioServer

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/workspace":
            self._send_json(HTTPStatus.OK, self.server.workspace.snapshot())
            return
        if path.startswith("/api/images/"):
            self._send_image(path)
            return
        if path.startswith("/api/thumbnails/"):
            self._send_thumbnail(path)
            return
        self._send_static(path)

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/pages/"):
            self._send_error(HTTPStatus.NOT_FOUND, "route not found")
            return
        try:
            page_number = int(path.removeprefix("/api/pages/"))
            payload = self._read_json()
            revision = payload.get("revision")
            if not isinstance(revision, str):
                raise ValueError("revision is required")
            page = GoldenPage.model_validate(payload.get("page"))
            if page.page_number != page_number:
                raise ValueError("request path and page number do not match")
            result = self.server.workspace.save_page(page, revision)
        except WorkspaceConflictError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
            return
        except (ValidationError, ValueError, json.JSONDecodeError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            return
        self._send_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            raise ValueError("request body size is invalid")
        payload = json.loads(self.rfile.read(content_length))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _send_image(self, path: str) -> None:
        try:
            page_number = int(path.removeprefix("/api/images/"))
            image_path = self.server.workspace.image_path(page_number)
        except (ValueError, FileNotFoundError) as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
            return
        self._send_bytes(HTTPStatus.OK, image_path.read_bytes(), "image/png")

    def _send_thumbnail(self, path: str) -> None:
        try:
            page_number = int(path.removeprefix("/api/thumbnails/"))
            thumbnail = self.server.workspace.thumbnail_bytes(page_number)
        except (ValueError, FileNotFoundError) as error:
            self._send_error(HTTPStatus.NOT_FOUND, str(error))
            return
        self._send_bytes(HTTPStatus.OK, thumbnail, "image/png")

    def _send_static(self, request_path: str) -> None:
        relative = request_path.lstrip("/") or "index.html"
        candidate = (self.server.static_root / relative).resolve()
        try:
            candidate.relative_to(self.server.static_root)
        except ValueError:
            self._send_error(HTTPStatus.NOT_FOUND, "route not found")
            return
        if not candidate.is_file():
            candidate = self.server.static_root / "index.html"
        if not candidate.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "studio frontend is not built")
            return
        media_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self._send_bytes(HTTPStatus.OK, candidate.read_bytes(), media_type)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        self._send_bytes(status, data, "application/json; charset=utf-8")

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"error": message})

    def _send_bytes(self, status: HTTPStatus, data: bytes, media_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; img-src 'self'; connect-src 'self'",
        )
        self.end_headers()
        self.wfile.write(data)


def serve_studio(
    workspace: GoldenWorkspace,
    static_root: Path,
    host: str,
    port: int,
) -> None:
    server = StudioServer((host, port), workspace, static_root)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
