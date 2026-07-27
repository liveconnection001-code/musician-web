#!/usr/bin/env python3
"""Deploy the reviewed Artist and achievements release with verified rollback."""

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
WORKSPACE = Path(r"A:\AI\Web\MUSICIAN")
ARTIST_ROOT = WORKSPACE / "new_site" / "artist_deployment"
COMPANY_TEMPLATE = (
    WORKSPACE / "new_site" / "seo_deployment" / "app" / "View"
    / "catalog" / "cl01_3" / "default" / "index.html"
)
ACHIEVEMENTS_CSS = (
    WORKSPACE / "new_site" / "deployment" / "app" / "webroot"
    / "css" / "recent_achievements.css"
)
ROLLBACK_ROOT = WORKSPACE / "new_site" / "production_backups"


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def safe_relative(relative: str) -> str:
    parts = PurePosixPath(relative).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise RuntimeError(f"Unsafe deployment path: {relative}")
    return PurePosixPath(*parts).as_posix()


def remote_for(relative: str) -> PurePosixPath:
    return PurePosixPath("/") / safe_relative(relative)


def deployment_rank(relative: str) -> tuple[int, str]:
    if relative.startswith("app/webroot/images/artists/megumi-omachi/"):
        return (0, relative)
    if relative.endswith("artist_megumi.css"):
        return (1, relative)
    if relative.endswith("recent_achievements.css"):
        return (2, relative)
    if relative.endswith("cl02_4/default/view.html"):
        return (3, relative)
    if relative.endswith("cl02_4/default/index.html"):
        return (4, relative)
    if relative == "app/View/Homes/index.html":
        return (5, relative)
    if relative.endswith("cl01_3/default/index.html"):
        return (6, relative)
    return (7, relative)


def load_targets() -> dict[str, bytes]:
    app_root = ARTIST_ROOT / "app"
    artist_files = sorted(path for path in app_root.rglob("*") if path.is_file())
    if len(artist_files) != 70:
        raise RuntimeError(f"Artist package must contain exactly 70 files, found {len(artist_files)}")

    targets: dict[str, bytes] = {}
    for path in artist_files:
        relative = safe_relative(path.relative_to(ARTIST_ROOT).as_posix())
        targets[relative] = path.read_bytes()

    image_paths = [
        relative for relative in targets
        if relative.startswith("app/webroot/images/artists/megumi-omachi/")
    ]
    if len(image_paths) != 66:
        raise RuntimeError(f"Megumi image package must contain 66 files, found {len(image_paths)}")
    if any(PurePosixPath(path).suffix.lower() not in (".jpg", ".webp") for path in image_paths):
        raise RuntimeError("Megumi public assets must be JPEG/WebP only")

    required_artist = {
        "app/View/Homes/index.html",
        "app/View/catalog/cl02_4/default/index.html",
        "app/View/catalog/cl02_4/default/view.html",
        "app/webroot/css/artist_megumi.css",
    }
    if not required_artist.issubset(targets):
        raise RuntimeError(f"Artist targets missing: {sorted(required_artist - set(targets))}")

    targets["app/View/catalog/cl01_3/default/index.html"] = COMPANY_TEMPLATE.read_bytes()
    targets["app/webroot/css/recent_achievements.css"] = ACHIEVEMENTS_CSS.read_bytes()
    if len(targets) != 72:
        raise RuntimeError(f"Combined deployment must contain exactly 72 files, found {len(targets)}")

    public_text = b"\n".join(
        payload for relative, payload in targets.items()
        if PurePosixPath(relative).suffix.lower() in (".html", ".css", ".php")
    ).decode("utf-8")
    if "株式会社MUSICIAN" in public_text:
        raise RuntimeError("Prohibited company name found in deployment")
    if "2019〜2026年" in targets["app/View/catalog/cl01_3/default/index.html"].decode("utf-8"):
        raise RuntimeError("Grouped achievements year label remains")
    return dict(sorted(targets.items(), key=lambda item: deployment_rank(item[0])))


def retrieve_optional(ftp: ftplib.FTP, remote: PurePosixPath) -> bytes | None:
    buffer = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {remote}", buffer.write)
    except ftplib.error_perm as exc:
        if str(exc).startswith("550"):
            return None
        raise
    return buffer.getvalue()


def delete_optional(ftp: ftplib.FTP, remote: PurePosixPath) -> None:
    try:
        ftp.delete(str(remote))
    except ftplib.error_perm as exc:
        if not str(exc).startswith("550"):
            raise


def ensure_remote_dir(ftp: ftplib.FTP, directory: PurePosixPath) -> None:
    current = PurePosixPath("/")
    for part in directory.parts[1:]:
        current /= part
        try:
            ftp.mkd(str(current))
        except ftplib.error_perm as exc:
            if not str(exc).startswith("550"):
                raise


def store_and_verify(ftp: ftplib.FTP, remote: PurePosixPath, payload: bytes) -> None:
    ensure_remote_dir(ftp, remote.parent)
    ftp.storbinary(f"STOR {remote}", io.BytesIO(payload), blocksize=1024 * 256)
    uploaded = retrieve_optional(ftp, remote)
    if uploaded is None or sha256(uploaded) != sha256(payload):
        raise RuntimeError(f"Remote hash verification failed: {remote}")


def new_backup_dir() -> tuple[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = (ROLLBACK_ROOT / f"artist_achievements_{stamp}").resolve()
    if ROLLBACK_ROOT.resolve() not in destination.parents:
        raise RuntimeError("Backup path escaped rollback root")
    destination.mkdir(parents=True, exist_ok=False)
    return stamp, destination


def write_manifest(backup_dir: Path, manifest: dict) -> None:
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_manifest(backup_dir_text: str) -> tuple[Path, dict]:
    backup_dir = Path(backup_dir_text).resolve()
    if ROLLBACK_ROOT.resolve() not in backup_dir.parents:
        raise RuntimeError("Rollback directory escaped rollback root")
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("host") != HOST:
        raise RuntimeError("Rollback manifest host mismatch")
    return backup_dir, manifest


def replace_target(
    ftp: ftplib.FTP,
    remote: PurePosixPath,
    payload: bytes,
    stamp: str,
    existed: bool,
) -> PurePosixPath | None:
    temp_remote = remote.with_name(f".{remote.name}.codex-upload-artist-{stamp}")
    backup_remote = remote.with_name(f".{remote.name}.codex-backup-artist-{stamp}")
    delete_optional(ftp, temp_remote)
    delete_optional(ftp, backup_remote)
    store_and_verify(ftp, temp_remote, payload)
    if existed:
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


def deploy(password: str) -> dict:
    targets = load_targets()
    stamp, backup_dir = new_backup_dir()
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": HOST,
        "status": "preparing",
        "summary": {
            "target_count": len(targets),
            "target_bytes": sum(len(payload) for payload in targets.values()),
            "artist_images": 66,
        },
        "targets": {},
    }

    with ftplib.FTP(HOST, timeout=40) as ftp:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")

        originals: dict[str, bytes | None] = {}
        original_root = backup_dir / "original"
        for relative, payload in targets.items():
            current = retrieve_optional(ftp, remote_for(relative))
            originals[relative] = current
            rollback_file = None
            if current is not None:
                path = original_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(current)
                rollback_file = str(path)
            manifest["targets"][relative] = {
                "remote": str(remote_for(relative)),
                "remote_existed": current is not None,
                "remote_size": len(current) if current is not None else None,
                "remote_sha256": sha256(current) if current is not None else None,
                "rollback_file": rollback_file,
                "deployment_size": len(payload),
                "deployment_sha256": sha256(payload),
                "remote_backup": None,
            }
        manifest["status"] = "backed_up"
        write_manifest(backup_dir, manifest)

        replaced: list[str] = []
        remote_backups: dict[str, PurePosixPath | None] = {}
        try:
            for relative, payload in targets.items():
                remote = remote_for(relative)
                remote_backups[relative] = replace_target(
                    ftp, remote, payload, stamp, originals[relative] is not None
                )
                manifest["targets"][relative]["remote_backup"] = (
                    str(remote_backups[relative]) if remote_backups[relative] else None
                )
                replaced.append(relative)
                write_manifest(backup_dir, manifest)

            for relative, payload in targets.items():
                deployed = retrieve_optional(ftp, remote_for(relative))
                if deployed is None or sha256(deployed) != sha256(payload):
                    raise RuntimeError(f"Final verification failed: {relative}")
        except Exception:
            rollback_errors = []
            for relative in reversed(replaced):
                try:
                    remote = remote_for(relative)
                    backup_remote = remote_backups.get(relative)
                    delete_optional(ftp, remote)
                    if backup_remote is not None:
                        ftp.rename(str(backup_remote), str(remote))
                    elif originals[relative] is not None:
                        store_and_verify(ftp, remote, originals[relative])
                except Exception as rollback_exc:
                    rollback_errors.append(f"{relative}: {rollback_exc}")
            manifest["status"] = "rolled_back_after_deployment_error"
            manifest["rollback_errors"] = rollback_errors
            write_manifest(backup_dir, manifest)
            if rollback_errors:
                raise RuntimeError("Deployment and rollback failed: " + "; ".join(rollback_errors))
            raise

    manifest["status"] = "deployed_pending_http_verification"
    manifest["deployed_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(backup_dir, manifest)
    return {
        "mode": "deploy",
        "backup_dir": str(backup_dir),
        "targets": len(targets),
        "status": manifest["status"],
    }


def rollback(password: str, backup_dir_text: str) -> dict:
    backup_dir, manifest = load_manifest(backup_dir_text)
    with ftplib.FTP(HOST, timeout=40) as ftp:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")
        for relative, entry in reversed(list(manifest["targets"].items())):
            remote = remote_for(relative)
            if entry["remote_existed"]:
                payload = Path(entry["rollback_file"]).read_bytes()
                if sha256(payload) != entry["remote_sha256"]:
                    raise RuntimeError(f"Rollback hash mismatch: {relative}")
                store_and_verify(ftp, remote, payload)
            else:
                delete_optional(ftp, remote)
            if entry.get("remote_backup"):
                delete_optional(ftp, PurePosixPath(entry["remote_backup"]))
    manifest["status"] = "rolled_back"
    manifest["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(backup_dir, manifest)
    return {"mode": "rollback", "backup_dir": str(backup_dir), "status": manifest["status"]}


def cleanup(password: str, backup_dir_text: str) -> dict:
    backup_dir, manifest = load_manifest(backup_dir_text)
    if manifest.get("status") != "deployed_pending_http_verification":
        raise RuntimeError(f"Refusing cleanup for status: {manifest.get('status')}")
    with ftplib.FTP(HOST, timeout=40) as ftp:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")
        for entry in manifest["targets"].values():
            if entry.get("remote_backup"):
                delete_optional(ftp, PurePosixPath(entry["remote_backup"]))
    manifest["status"] = "deployed_verified"
    manifest["remote_backups_cleaned_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(backup_dir, manifest)
    return {"mode": "cleanup", "backup_dir": str(backup_dir), "status": manifest["status"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "deploy", "rollback", "cleanup"))
    parser.add_argument("--backup-dir")
    args = parser.parse_args()
    if args.mode == "plan":
        targets = load_targets()
        print(json.dumps({
            "mode": "plan",
            "targets": len(targets),
            "bytes": sum(len(payload) for payload in targets.values()),
            "paths": list(targets),
        }, ensure_ascii=False))
        return 0
    password = os.environ.get(PASSWORD_ENV)
    if not password:
        raise RuntimeError(f"{PASSWORD_ENV} is not set")
    if args.mode == "deploy":
        result = deploy(password)
    else:
        if not args.backup_dir:
            raise RuntimeError("--backup-dir is required")
        result = rollback(password, args.backup_dir) if args.mode == "rollback" else cleanup(password, args.backup_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
