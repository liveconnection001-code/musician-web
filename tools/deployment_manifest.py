from __future__ import annotations

import hashlib
from pathlib import PurePosixPath


TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".php",
    ".txt",
    ".xml",
}
TEXT_FILENAMES = {".htaccess"}


def canonical_manifest_payload(relative_path: str, payload: bytes) -> bytes:
    """Return the cross-platform representation used for manifest integrity."""
    path = PurePosixPath(relative_path)
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_FILENAMES:
        return payload.replace(b"\r\n", b"\n")
    return payload


def manifest_metadata(relative_path: str, payload: bytes) -> tuple[int, str]:
    canonical = canonical_manifest_payload(relative_path, payload)
    return len(canonical), hashlib.sha256(canonical).hexdigest()
