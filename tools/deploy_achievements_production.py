#!/usr/bin/env python3
"""Inspect or deploy the approved MUSICIAN achievements update over FTP.

The script is deliberately limited to the company-page view and its dedicated
stylesheet. It saves an exact local rollback copy before any production write.
"""

from __future__ import annotations

import argparse
import ftplib
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


HOST = "ftp.musician.co.jp"
USER = "codex_bk_0725@musician.co.jp"
PASSWORD_ENV = "MUSICIAN_TEMP_FTP_PASSWORD"
WORKSPACE = Path(os.environ.get("MUSICIAN_WORKSPACE", Path(__file__).resolve().parents[1]))
ROLLBACK_ROOT = WORKSPACE / "new_site" / "production_backups"

TARGETS = {
    "company_view": {
        "remote": PurePosixPath(
            "/app/View/catalog/cl01_3/default/index.html"
        ),
        "local": WORKSPACE
        / "new_site"
        / "deployment"
        / "app"
        / "View"
        / "catalog"
        / "cl01_3"
        / "default"
        / "index.html",
    },
    "achievements_css": {
        "remote": PurePosixPath("/app/webroot/css/recent_achievements.css"),
        "local": WORKSPACE
        / "new_site"
        / "deployment"
        / "app"
        / "webroot"
        / "css"
        / "recent_achievements.css",
    },
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def retrieve_optional(ftp: ftplib.FTP, remote: PurePosixPath) -> bytes | None:
    buffer = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {remote}", buffer.write)
    except ftplib.error_perm as exc:
        if str(exc).startswith("550"):
            return None
        raise
    return buffer.getvalue()


def store_and_verify(
    ftp: ftplib.FTP, remote: PurePosixPath, payload: bytes
) -> None:
    ftp.storbinary(
        f"STOR {remote}", io.BytesIO(payload), blocksize=1024 * 256
    )
    uploaded = retrieve_optional(ftp, remote)
    if uploaded is None or sha256(uploaded) != sha256(payload):
        raise RuntimeError(f"Remote verification failed: {remote}")


def safe_backup_dir(stamp: str) -> Path:
    backup_dir = (ROLLBACK_ROOT / stamp).resolve()
    root = ROLLBACK_ROOT.resolve()
    if root not in backup_dir.parents:
        raise RuntimeError("Refusing backup path outside rollback root")
    backup_dir.mkdir(parents=True, exist_ok=False)
    return backup_dir


def write_rollback(
    backup_dir: Path,
    current: dict[str, bytes | None],
    local: dict[str, bytes],
) -> dict:
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": HOST,
        "targets": {},
    }
    for name, target in TARGETS.items():
        remote_data = current[name]
        if remote_data is not None:
            rollback_file = backup_dir / f"{name}.original"
            rollback_file.write_bytes(remote_data)
            rollback_path = str(rollback_file)
            remote_hash = sha256(remote_data)
            remote_size = len(remote_data)
        else:
            rollback_path = None
            remote_hash = None
            remote_size = None
        manifest["targets"][name] = {
            "remote": str(target["remote"]),
            "remote_existed": remote_data is not None,
            "remote_size": remote_size,
            "remote_sha256": remote_hash,
            "rollback_file": rollback_path,
            "deployment_size": len(local[name]),
            "deployment_sha256": sha256(local[name]),
        }
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def replace_target(
    ftp: ftplib.FTP,
    remote: PurePosixPath,
    payload: bytes,
    stamp: str,
) -> PurePosixPath | None:
    temp_remote = remote.with_name(f".{remote.name}.codex-upload-{stamp}")
    backup_remote = remote.with_name(f".{remote.name}.codex-backup-{stamp}")
    store_and_verify(ftp, temp_remote, payload)

    existing = retrieve_optional(ftp, remote)
    if existing is not None:
        ftp.rename(str(remote), str(backup_remote))
        remote_backup: PurePosixPath | None = backup_remote
    else:
        remote_backup = None

    try:
        ftp.rename(str(temp_remote), str(remote))
    except Exception:
        if remote_backup is not None:
            ftp.rename(str(remote_backup), str(remote))
        raise
    return remote_backup


def restore_target(
    ftp: ftplib.FTP,
    remote: PurePosixPath,
    original: bytes | None,
) -> None:
    if original is None:
        try:
            ftp.delete(str(remote))
        except ftplib.error_perm as exc:
            if not str(exc).startswith("550"):
                raise
    else:
        store_and_verify(ftp, remote, original)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("inspect", "deploy"))
    args = parser.parse_args()

    password = os.environ.get(PASSWORD_ENV)
    if not password:
        raise RuntimeError(f"{PASSWORD_ENV} is not set")

    local: dict[str, bytes] = {}
    for name, target in TARGETS.items():
        local_path = target["local"]
        if not local_path.is_file():
            raise RuntimeError(f"Deployment source missing: {local_path}")
        local[name] = local_path.read_bytes()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with ftplib.FTP(HOST, timeout=30) as ftp:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")

        current = {
            name: retrieve_optional(ftp, target["remote"])
            for name, target in TARGETS.items()
        }
        backup_dir = safe_backup_dir(stamp)
        manifest = write_rollback(backup_dir, current, local)

        if args.mode == "inspect":
            result = {
                "mode": "inspect",
                "backup_dir": str(backup_dir),
                "targets": manifest["targets"],
            }
            print(json.dumps(result, ensure_ascii=False))
            return 0

        replaced: list[str] = []
        remote_backups: dict[str, PurePosixPath | None] = {}
        try:
            # The stylesheet is made available before the HTML begins using it.
            for name in ("achievements_css", "company_view"):
                target = TARGETS[name]
                remote_backups[name] = replace_target(
                    ftp, target["remote"], local[name], stamp
                )
                replaced.append(name)

            verification = {}
            for name, target in TARGETS.items():
                deployed = retrieve_optional(ftp, target["remote"])
                if deployed is None or sha256(deployed) != sha256(local[name]):
                    raise RuntimeError(f"Final verification failed: {name}")
                verification[name] = {
                    "size": len(deployed),
                    "sha256": sha256(deployed),
                }
        except Exception:
            for name in reversed(replaced):
                restore_target(
                    ftp, TARGETS[name]["remote"], current[name]
                )
            raise

    print(
        json.dumps(
            {
                "mode": "deploy",
                "backup_dir": str(backup_dir),
                "verification": verification,
                "url": "https://www.musician.co.jp/company.html#achievements",
                "remote_backups": {
                    name: str(path) if path is not None else None
                    for name, path in remote_backups.items()
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


