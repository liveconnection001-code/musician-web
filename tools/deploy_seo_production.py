#!/usr/bin/env python3
"""Deploy or roll back the approved MUSICIAN SEO package over FTP.

The deployment is restricted to an explicit list of 18 production files. Each
existing remote file is saved locally before the first production write. New
content is uploaded to a hidden temporary name, hash-verified, then renamed into
place. Any deployment error rolls back every file changed in the current run.
"""

from __future__ import annotations

import argparse
import ftplib
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from tempfile import gettempdir
from pathlib import Path, PurePosixPath


HOST = "ftp.musician.co.jp"
USER = "codex_bk_0725@musician.co.jp"
PASSWORD_ENV = "MUSICIAN_TEMP_FTP_PASSWORD"
WORKSPACE = Path(os.environ.get("MUSICIAN_WORKSPACE", Path(__file__).resolve().parents[1]))
PACKAGE_ROOT = WORKSPACE / "new_site" / "seo_deployment"
PACKAGE_MANIFEST = PACKAGE_ROOT / "seo_manifest.json"
ROLLBACK_ROOT = WORKSPACE / "new_site" / "production_backups"


def resolve_rollback_root() -> Path:
    candidates = [WORKSPACE / "new_site" / "production_backups", Path(gettempdir()) / "musician_production_backups"]
    env_root = os.environ.get("MUSICIAN_ROLLBACK_ROOT")
    if env_root:
        candidates.insert(0, Path(env_root))

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".codex_write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return candidate.resolve()
        except OSError:
            continue
    raise RuntimeError("No writable rollback root available")

ROLLBACK_ROOT = resolve_rollback_root()

# Dependencies first; routing and rewrite rules last.
DEPLOYMENT_PATHS = (
    "app/View/Elements/seo_meta.html",
    "app/webroot/css/style.css",
    "app/webroot/sitemap.xml",
    "app/View/Homes/robots.html",
    "app/View/Errors/error400.html",
    "app/Controller/HomesController.php",
    "app/View/Homes/index.html",
    "app/webroot/business.html",
    "app/webroot/contact.html",
    "app/View/catalog/cl01_2/default/index.html",
    "app/View/catalog/cl01_3/default/index.html",
    "app/View/catalog/cl02_4/default/index.html",
    "app/View/catalog/cl02_4/default/view.html",
    "app/View/Contact/msg.html",
    "app/View/Contact/thanks.html",
    "app/Config/routes.php",
    "app/webroot/.htaccess",
    ".htaccess",
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def remote_for(relative_path: str) -> PurePosixPath:
    parts = PurePosixPath(relative_path).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise RuntimeError(f"Unsafe deployment path: {relative_path}")
    return PurePosixPath("/").joinpath(*parts)


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


def store_and_verify(ftp: ftplib.FTP, remote: PurePosixPath, payload: bytes) -> None:
    ftp.storbinary(f"STOR {remote}", io.BytesIO(payload), blocksize=1024 * 256)
    uploaded = retrieve_optional(ftp, remote)
    if uploaded is None or sha256(uploaded) != sha256(payload):
        raise RuntimeError(f"Remote verification failed: {remote}")


def load_and_verify_package() -> dict[str, bytes]:
    manifest = json.loads(PACKAGE_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("file_count") < len(DEPLOYMENT_PATHS):
        raise RuntimeError("SEO package manifest must include at least all deployment files")
    manifest_files = {entry["path"]: entry for entry in manifest.get("files", [])}
    if "CLAUDE_REVIEW.md" in manifest_files:
        raise RuntimeError("Review documentation must not be in the deployment manifest")

    local: dict[str, bytes] = {}
    for relative_path in DEPLOYMENT_PATHS:
        entry = manifest_files.get(relative_path)
        if entry is None:
            raise RuntimeError(f"Manifest entry missing: {relative_path}")
        local_path = (PACKAGE_ROOT / relative_path).resolve()
        if PACKAGE_ROOT.resolve() not in local_path.parents:
            raise RuntimeError(f"Local source escaped package root: {relative_path}")
        payload = local_path.read_bytes()
        if len(payload) != entry["bytes"] or sha256(payload) != entry["sha256"]:
            raise RuntimeError(f"Local package hash mismatch: {relative_path}")
        local[relative_path] = payload
    if len(local) != len(DEPLOYMENT_PATHS):
        raise RuntimeError(f"Expected {len(DEPLOYMENT_PATHS)} production targets, got {len(local)}")
    return local


def new_backup_dir() -> tuple[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = (ROLLBACK_ROOT / f"seo_{stamp}").resolve()
    if ROLLBACK_ROOT.resolve() not in backup_dir.parents:
        raise RuntimeError("Refusing backup path outside rollback root")
    backup_dir.mkdir(parents=True, exist_ok=False)
    return stamp, backup_dir


def save_rollback(
    backup_dir: Path,
    current: dict[str, bytes | None],
    local: dict[str, bytes],
) -> dict:
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": HOST,
        "status": "backed_up",
        "targets": {},
    }
    original_root = backup_dir / "original"
    for relative_path in DEPLOYMENT_PATHS:
        remote_data = current[relative_path]
        rollback_path = None
        if remote_data is not None:
            rollback_file = original_root / relative_path
            rollback_file.parent.mkdir(parents=True, exist_ok=True)
            rollback_file.write_bytes(remote_data)
            rollback_path = str(rollback_file)
        manifest["targets"][relative_path] = {
            "remote": str(remote_for(relative_path)),
            "remote_existed": remote_data is not None,
            "remote_size": len(remote_data) if remote_data is not None else None,
            "remote_sha256": sha256(remote_data) if remote_data is not None else None,
            "rollback_file": rollback_path,
            "deployment_size": len(local[relative_path]),
            "deployment_sha256": sha256(local[relative_path]),
            "remote_backup": None,
        }
    write_manifest(backup_dir, manifest)
    return manifest


def write_manifest(backup_dir: Path, manifest: dict) -> None:
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def replace_target(
    ftp: ftplib.FTP,
    remote: PurePosixPath,
    payload: bytes,
    stamp: str,
) -> PurePosixPath | None:
    temp_remote = remote.with_name(f".{remote.name}.codex-upload-seo-{stamp}")
    backup_remote = remote.with_name(f".{remote.name}.codex-backup-seo-{stamp}")
    delete_optional(ftp, temp_remote)
    delete_optional(ftp, backup_remote)
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


def restore_from_memory(
    ftp: ftplib.FTP,
    relative_path: str,
    original: bytes | None,
    remote_backup: PurePosixPath | None,
) -> None:
    remote = remote_for(relative_path)
    if remote_backup is not None:
        delete_optional(ftp, remote)
        ftp.rename(str(remote_backup), str(remote))
    elif original is None:
        delete_optional(ftp, remote)
    else:
        store_and_verify(ftp, remote, original)


def deploy(password: str) -> dict:
    local = load_and_verify_package()
    stamp, backup_dir = new_backup_dir()
    with ftplib.FTP(HOST, timeout=30) as ftp:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")

        current = {
            relative_path: retrieve_optional(ftp, remote_for(relative_path))
            for relative_path in DEPLOYMENT_PATHS
        }
        manifest = save_rollback(backup_dir, current, local)
        replaced: list[str] = []
        remote_backups: dict[str, PurePosixPath | None] = {}
        try:
            for relative_path in DEPLOYMENT_PATHS:
                remote = remote_for(relative_path)
                remote_backups[relative_path] = replace_target(
                    ftp, remote, local[relative_path], stamp
                )
                manifest["targets"][relative_path]["remote_backup"] = (
                    str(remote_backups[relative_path])
                    if remote_backups[relative_path] is not None
                    else None
                )
                replaced.append(relative_path)
                write_manifest(backup_dir, manifest)

            for relative_path in DEPLOYMENT_PATHS:
                deployed = retrieve_optional(ftp, remote_for(relative_path))
                if deployed is None or sha256(deployed) != sha256(local[relative_path]):
                    raise RuntimeError(f"Final verification failed: {relative_path}")
        except Exception:
            rollback_errors = []
            for relative_path in reversed(replaced):
                try:
                    restore_from_memory(
                        ftp,
                        relative_path,
                        current[relative_path],
                        remote_backups.get(relative_path),
                    )
                except Exception as rollback_exc:
                    rollback_errors.append(f"{relative_path}: {rollback_exc}")
            manifest["status"] = "rolled_back_after_deployment_error"
            manifest["rollback_errors"] = rollback_errors
            write_manifest(backup_dir, manifest)
            if rollback_errors:
                raise RuntimeError(
                    "Deployment failed and rollback had errors: "
                    + "; ".join(rollback_errors)
                )
            raise

    manifest["status"] = "deployed_pending_http_verification"
    manifest["deployed_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(backup_dir, manifest)
    return {
        "mode": "deploy",
        "backup_dir": str(backup_dir),
        "targets": len(DEPLOYMENT_PATHS),
        "status": manifest["status"],
    }


def load_rollback_manifest(backup_dir_text: str) -> tuple[Path, dict]:
    backup_dir = Path(backup_dir_text).resolve()
    if ROLLBACK_ROOT.resolve() not in backup_dir.parents:
        raise RuntimeError("Refusing rollback directory outside rollback root")
    manifest_path = backup_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("host") != HOST:
        raise RuntimeError("Rollback manifest host mismatch")
    return backup_dir, manifest


def rollback(password: str, backup_dir_text: str) -> dict:
    backup_dir, manifest = load_rollback_manifest(backup_dir_text)
    with ftplib.FTP(HOST, timeout=30) as ftp:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")
        for relative_path in reversed(DEPLOYMENT_PATHS):
            entry = manifest["targets"][relative_path]
            remote = remote_for(relative_path)
            if entry["remote_existed"]:
                original = Path(entry["rollback_file"]).read_bytes()
                if sha256(original) != entry["remote_sha256"]:
                    raise RuntimeError(f"Rollback file hash mismatch: {relative_path}")
                store_and_verify(ftp, remote, original)
            else:
                delete_optional(ftp, remote)
        for relative_path in DEPLOYMENT_PATHS:
            entry = manifest["targets"][relative_path]
            current = retrieve_optional(ftp, remote_for(relative_path))
            if entry["remote_existed"]:
                if current is None or sha256(current) != entry["remote_sha256"]:
                    raise RuntimeError(f"Rollback verification failed: {relative_path}")
            elif current is not None:
                raise RuntimeError(f"Rollback deletion failed: {relative_path}")
    manifest["status"] = "rolled_back"
    manifest["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(backup_dir, manifest)
    return {"mode": "rollback", "backup_dir": str(backup_dir), "status": "rolled_back"}


def cleanup(password: str, backup_dir_text: str) -> dict:
    backup_dir, manifest = load_rollback_manifest(backup_dir_text)
    if manifest.get("status") not in (
        "deployed_pending_http_verification",
        "deployed_verified",
    ):
        raise RuntimeError(f"Refusing cleanup for status: {manifest.get('status')}")
    with ftplib.FTP(HOST, timeout=30) as ftp:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")
        for entry in manifest["targets"].values():
            if entry.get("remote_backup"):
                delete_optional(ftp, PurePosixPath(entry["remote_backup"]))
    manifest["status"] = "deployed_verified"
    manifest["remote_backups_cleaned_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(backup_dir, manifest)
    return {"mode": "cleanup", "backup_dir": str(backup_dir), "status": "deployed_verified"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("deploy", "rollback", "cleanup"))
    parser.add_argument("--backup-dir")
    args = parser.parse_args()
    password = os.environ.get(PASSWORD_ENV)
    if not password:
        raise RuntimeError(f"{PASSWORD_ENV} is not set")
    if args.mode == "deploy":
        result = deploy(password)
    else:
        if not args.backup_dir:
            raise RuntimeError("--backup-dir is required")
        result = (
            rollback(password, args.backup_dir)
            if args.mode == "rollback"
            else cleanup(password, args.backup_dir)
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())








