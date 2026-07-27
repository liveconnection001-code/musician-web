#!/usr/bin/env python3
"""Upload the public-only MUSICIAN review page to an isolated FTP directory."""

from __future__ import annotations

import ftplib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


HOST = "ftp.musician.co.jp"
USER = "codex_bk_0725@musician.co.jp"
LOCAL_ROOT = Path(r"A:\AI\Web\MUSICIAN\temporary_preview_site\public")
REMOTE_ROOT = PurePosixPath("/app/webroot/preview-achievements-20260726-8a2f")
MARKER_NAME = ".codex-preview.json"
MARKER_ID = "musician-achievements-20260726-8a2f"


def safe_remote(relative: Path) -> str:
    parts = [part for part in relative.parts if part not in ("", ".")]
    if any(part in ("..",) for part in parts):
        raise RuntimeError(f"Unsafe relative path: {relative}")
    remote = REMOTE_ROOT.joinpath(*parts)
    remote_text = str(remote)
    prefix = str(REMOTE_ROOT).rstrip("/") + "/"
    if remote_text != str(REMOTE_ROOT) and not remote_text.startswith(prefix):
        raise RuntimeError(f"Refusing path outside preview root: {remote_text}")
    return remote_text


def ensure_dir(ftp: ftplib.FTP, remote_dir: PurePosixPath) -> None:
    current = PurePosixPath("/")
    for part in remote_dir.parts:
        if part in ("", "/"):
            continue
        current = current / part
        try:
            ftp.mkd(str(current))
        except ftplib.error_perm as exc:
            if not str(exc).startswith("550"):
                raise


def read_marker(ftp: ftplib.FTP) -> dict | None:
    payload = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {REMOTE_ROOT / MARKER_NAME}", payload.write)
    except ftplib.error_perm as exc:
        if str(exc).startswith("550"):
            return None
        raise
    return json.loads(payload.getvalue().decode("utf-8"))


def public_files() -> list[Path]:
    files = []
    for path in LOCAL_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name.lower() == "thumbs.db" or path.name.startswith("."):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(LOCAL_ROOT).as_posix())


def main() -> int:
    password = os.environ.get("MUSICIAN_TEMP_FTP_PASSWORD")
    if not password:
        raise RuntimeError("MUSICIAN_TEMP_FTP_PASSWORD is not set")
    if not LOCAL_ROOT.is_dir():
        raise RuntimeError(f"Preview directory not found: {LOCAL_ROOT}")

    files = public_files()
    if not files or not (LOCAL_ROOT / "company.html").is_file():
        raise RuntimeError("Preview payload is incomplete")

    with ftplib.FTP(HOST, timeout=30) as ftp:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")

        marker = read_marker(ftp)
        if marker is not None and marker.get("id") != MARKER_ID:
            raise RuntimeError("Existing remote directory is not this preview")

        ensure_dir(ftp, REMOTE_ROOT)
        if marker is None:
            marker_payload = json.dumps(
                {
                    "id": MARKER_ID,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "purpose": "MUSICIAN achievements review preview",
                },
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            ftp.storbinary(
                f"STOR {REMOTE_ROOT / MARKER_NAME}", io.BytesIO(marker_payload)
            )

        uploaded_bytes = 0
        for local_path in files:
            relative = local_path.relative_to(LOCAL_ROOT)
            remote_path = safe_remote(relative)
            ensure_dir(ftp, PurePosixPath(remote_path).parent)
            with local_path.open("rb") as stream:
                ftp.storbinary(f"STOR {remote_path}", stream, blocksize=1024 * 256)
            expected = local_path.stat().st_size
            actual = ftp.size(remote_path)
            if actual != expected:
                raise RuntimeError(
                    f"Size mismatch for {relative}: expected {expected}, got {actual}"
                )
            uploaded_bytes += expected

    print(
        json.dumps(
            {
                "files": len(files),
                "bytes": uploaded_bytes,
                "remote_root": str(REMOTE_ROOT),
                "company_url": "https://www.musician.co.jp/preview-achievements-20260726-8a2f/company.html",
                "home_url": "https://www.musician.co.jp/preview-achievements-20260726-8a2f/home.html",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
