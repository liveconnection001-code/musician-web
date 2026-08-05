#!/usr/bin/env python3
"""Atomic full-site deployment and verified removal of obsolete server remnants."""

from __future__ import annotations

import argparse
import ftplib
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from tempfile import gettempdir
from pathlib import Path, PurePosixPath

from deployment_manifest import manifest_metadata


HOST = "ftp.musician.co.jp"
USER = "codex_bk_0725@musician.co.jp"
PASSWORD_ENV = "MUSICIAN_TEMP_FTP_PASSWORD"
WORKSPACE = Path(os.environ.get("MUSICIAN_WORKSPACE", Path(__file__).resolve().parents[1]))
SEO_ROOT = WORKSPACE / "new_site" / "seo_deployment"
SEO_MANIFEST = SEO_ROOT / "seo_manifest.json"
WORKS_ROOT = WORKSPACE / "new_site" / "works_deployment"
WORKS_GALLERY_MANIFEST = WORKS_ROOT / "performance_gallery_manifest.json"
ARTIST_ROOT = WORKSPACE / "new_site" / "artist_deployment"
ACHIEVEMENTS_CSS = WORKSPACE / "new_site" / "deployment" / "app" / "webroot" / "css" / "recent_achievements.css"
ROLLBACK_ROOT = WORKSPACE / "new_site" / "production_backups"
LEGACY_GALLERY_ASSETS = {
    f"app/webroot/images/works/gallery/{key}-{variant}.{extension}"
    for key in ("traditional-taiko", "unit-big-band", "unit-live-band")
    for variant, extension in (
        ("small", "webp"),
        ("card", "webp"),
        ("card", "jpg"),
        ("large", "jpg"),
    )
}


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
FULL_BACKUP = WORKSPACE / "backup_2026-07-25" / "site_files"

# Confirmed duplicate, sample, diagnostic, or superseded paths. Active /admin,
# CakePHP /app, /lib, captcha core files, media, and hosting-managed paths remain.
OBSOLETE_PATHS = (
    "/admin_sp",
    "/_dl",
    "/_bk_20221124",
    "/report.html",
    "/app/Controller/SampleKit",
    "/app/View/SampleKit",
    "/app/webroot/SampleKit",
    "/app/Controller/LinkcheckController.php",
    "/app/View/Linkcheck",
    "/app/webroot/ez_js/eq",
    "/app/webroot/ez_js/pdf/web",
    "/app/webroot/securimage/captcha.html",
    "/app/webroot/securimage/config.inc.php.SAMPLE",
    "/app/webroot/securimage/example_form.ajax.php",
    "/app/webroot/securimage/example_form.php",
    "/app/webroot/securimage/README.FONT.txt",
    "/app/webroot/securimage/README.md",
    "/app/webroot/securimage/README.txt",
    "/app/webroot/images/works/gallery/traditional-taiko-small.webp",
    "/app/webroot/images/works/gallery/traditional-taiko-card.webp",
    "/app/webroot/images/works/gallery/traditional-taiko-card.jpg",
    "/app/webroot/images/works/gallery/traditional-taiko-large.jpg",
    "/app/webroot/images/works/gallery/unit-big-band-small.webp",
    "/app/webroot/images/works/gallery/unit-big-band-card.webp",
    "/app/webroot/images/works/gallery/unit-big-band-card.jpg",
    "/app/webroot/images/works/gallery/unit-big-band-large.jpg",
    "/app/webroot/images/works/gallery/unit-live-band-small.webp",
    "/app/webroot/images/works/gallery/unit-live-band-card.webp",
    "/app/webroot/images/works/gallery/unit-live-band-card.jpg",
    "/app/webroot/images/works/gallery/unit-live-band-large.jpg",
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def warn(message: str) -> None:
    print(f"[WARN] {message}", file=sys.stderr)


def safe_relative(relative: str) -> str:
    parts = PurePosixPath(relative).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise RuntimeError(f"Unsafe deployment path: {relative}")
    return PurePosixPath(*parts).as_posix()


def remote_for(relative: str) -> PurePosixPath:
    return PurePosixPath("/") / safe_relative(relative)


def retrieve_optional(ftp: ftplib.FTP, remote: PurePosixPath) -> bytes | None:
    buffer = io.BytesIO()
    try:
        ftp.retrbinary(f"RETR {remote}", buffer.write)
    except ftplib.error_perm as exc:
        if str(exc).startswith("550"):
            return None
        raise
    return buffer.getvalue()


def delete_file_optional(ftp: ftplib.FTP, remote: PurePosixPath) -> None:
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


def remote_kind(ftp: ftplib.FTP, remote: PurePosixPath) -> str | None:
    if remote == PurePosixPath("/"):
        return "dir"
    parent = remote.parent
    name = remote.name
    try:
        for entry_name, facts in ftp.mlsd(str(parent)):
            if entry_name == name:
                kind = facts.get("type", "")
                return "dir" if kind in ("dir", "cdir", "pdir") else "file"
    except ftplib.error_perm as exc:
        if not str(exc).startswith("550"):
            raise
    return None


def login_ftp(password: str, *, timeout: int = 40) -> ftplib.FTP:
    ftp = ftplib.FTP(HOST, timeout=timeout)
    try:
        ftp.login(USER, password)
        ftp.set_pasv(True)
        ftp.voidcmd("TYPE I")
        return ftp
    except ftplib.error_perm as exc:
        ftp.close()
        if str(exc).startswith("530"):
            raise RuntimeError(
                f"FTP認証に失敗しました（user={USER}, host={HOST}）。"
                " 環境変数 MUSICIAN_TEMP_FTP_PASSWORD が正しいか確認してください。"
            ) from exc
        raise


def remove_tree(ftp: ftplib.FTP, remote: PurePosixPath) -> int:
    kind = remote_kind(ftp, remote)
    if kind is None:
        return 0
    if kind == "file":
        try:
            ftp.delete(str(remote))
        except ftplib.error_perm as exc:
            if not str(exc).startswith("550"):
                raise
            return 0
        return 1
    removed = 0
    try:
        entries = list(ftp.mlsd(str(remote)))
    except ftplib.error_perm as exc:
        if not str(exc).startswith("550"):
            raise
        return 0
    for name, facts in entries:
        if name in (".", "..") or facts.get("type") in ("cdir", "pdir"):
            continue
        child = remote / name
        if facts.get("type") == "dir":
            removed += remove_tree(ftp, child)
        else:
            try:
                ftp.delete(str(child))
                removed += 1
            except ftplib.error_perm as exc:
                if not str(exc).startswith("550"):
                    raise
    try:
        ftp.rmd(str(remote))
    except ftplib.error_perm as exc:
        if not str(exc).startswith("550"):
            raise
    return removed


def read_local_targets() -> tuple[dict[str, bytes], dict]:
    manifest = json.loads(SEO_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("file_count") != 39:
        warn(f"SEO manifest file_count is {manifest.get('file_count')}, expected 39.")
    manifest_files = {entry["path"]: entry for entry in manifest["files"]}
    manifest_mismatches: list[str] = []

    targets: dict[str, bytes] = {}
    for relative, entry in manifest_files.items():
        if relative in ("README.md", "app/View/catalog/cl01_2/default/index.html"):
            continue
        relative = safe_relative(relative)
        local_path = SEO_ROOT / relative
        if not local_path.exists():
            warn(f"SEO manifest refers to missing file: {relative}")
            continue
        payload = local_path.read_bytes()
        payload_size, payload_hash = manifest_metadata(relative, payload)
        if payload_size != entry.get("bytes") or payload_hash != entry.get("sha256"):
            manifest_mismatches.append(relative)
        targets[relative] = payload
    if manifest_mismatches:
        warn(f"SEO manifest hash mismatch for: {', '.join(manifest_mismatches)}")

    # Artist is a reviewed source package. Merge it into the same atomic release
    # so a Works/SEO deployment can never silently restore the old listing or
    # omit Megumi Omachi's detail page and supplied image assets.
    artist_files = sorted((ARTIST_ROOT / "app").rglob("*"))
    for path in artist_files:
        if not path.is_file():
            continue
        relative = path.relative_to(ARTIST_ROOT).as_posix()
        targets[safe_relative(relative)] = path.read_bytes()

    works_files = sorted((WORKS_ROOT / "app").rglob("*"))
    for path in works_files:
        if not path.is_file():
            continue
        relative = path.relative_to(WORKS_ROOT).as_posix()
        if relative in LEGACY_GALLERY_ASSETS:
            continue
        targets[safe_relative(relative)] = path.read_bytes()

    targets["app/webroot/css/recent_achievements.css"] = ACHIEVEMENTS_CSS.read_bytes()

    works_root_image_names = [
        PurePosixPath(path).name
        for path in targets
        if PurePosixPath(path).parent == PurePosixPath("app/webroot/images/works")
        and PurePosixPath(path).suffix.lower() in (".jpg", ".jpeg", ".webp")
    ]
    if len(works_root_image_names) != 14 or any("-clean" not in name for name in works_root_image_names):
        raise RuntimeError("Works public assets must be exactly 14 clean JPEG/WebP files")

    gallery_manifest = json.loads(WORKS_GALLERY_MANIFEST.read_text(encoding="utf-8"))
    gallery_keys = [entry["key"] for entry in gallery_manifest.get("photos", [])]
    # Remove accidental duplicates but keep deterministic latest content order.
    gallery_keys = list(dict.fromkeys(gallery_keys))
    if len(gallery_keys) == 0:
        raise RuntimeError("Works gallery has no photos")
    actual_gallery = {
        path
        for path in targets
        if PurePosixPath(path).parent == PurePosixPath("app/webroot/images/works/gallery")
    }
    for key in gallery_keys:
        prefix = f"app/webroot/images/works/gallery/{key}-"
        has_file = any(item.startswith(prefix) for item in actual_gallery)
        if not has_file:
            raise RuntimeError(f"Works gallery key has no deployed file: {key}")

    if "app/View/catalog/cl01_2/default/index.html" not in targets:
        raise RuntimeError("Curated Works template is missing")
    if "app/webroot/css/works_showcase.css" not in targets:
        raise RuntimeError("Works stylesheet is missing")
    if "app/View/catalog/cl02_4/default/index.html" not in targets:
        raise RuntimeError("Reviewed Artist listing is missing")
    if "app/View/catalog/cl02_4/default/view.html" not in targets:
        raise RuntimeError("Reviewed Artist detail template is missing")
    if "app/webroot/css/artist_megumi.css" not in targets:
        raise RuntimeError("Megumi Artist stylesheet is missing")

    ordered = dict(
        sorted(
            targets.items(),
            key=lambda item: (
                item[0] in ("app/Config/routes.php", "app/webroot/.htaccess", ".htaccess", "admin/.htaccess"),
                item[0].endswith(".html") or item[0].endswith(".php"),
                item[0],
            ),
        )
    )
    summary = {
        "target_count": len(ordered),
        "target_bytes": sum(len(value) for value in ordered.values()),
        "works_images": len(works_root_image_names),
        "works_gallery_images": len(actual_gallery),
        "artist_files": len(artist_files),
        "manifest_file_count": manifest.get("file_count"),
        "manifest_mismatches": manifest_mismatches,
    }
    return ordered, summary


def new_backup_dir() -> tuple[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = (ROLLBACK_ROOT / f"full_{stamp}").resolve()
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


def deploy(password: str) -> dict:
    if not (FULL_BACKUP / ".ftp_state.json").is_file():
        raise RuntimeError("Complete pre-deployment FTP backup checkpoint is missing")
    targets, summary = read_local_targets()
    stamp, backup_dir = new_backup_dir()
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": HOST,
        "status": "preparing",
        "complete_backup": str(FULL_BACKUP),
        "summary": summary,
        "targets": {},
        "quarantines": [],
    }

    with login_ftp(password, timeout=40) as ftp:

        originals: dict[str, bytes | None] = {}
        original_root = backup_dir / "original"
        for relative, payload in targets.items():
            remote = remote_for(relative)
            current = retrieve_optional(ftp, remote)
            originals[relative] = current
            rollback_file = None
            if current is not None:
                rollback_path = original_root / relative
                rollback_path.parent.mkdir(parents=True, exist_ok=True)
                rollback_path.write_bytes(current)
                rollback_file = str(rollback_path)
            manifest["targets"][relative] = {
                "remote": str(remote),
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

        changed_targets = {
            relative: payload
            for relative, payload in targets.items()
            if originals[relative] is None or sha256(originals[relative]) != sha256(payload)
        }
        for relative in targets:
            manifest["targets"][relative]["changed"] = relative in changed_targets
        summary["changed_target_count"] = len(changed_targets)
        manifest["summary"]["changed_target_count"] = summary["changed_target_count"]
        write_manifest(backup_dir, manifest)

        replaced: list[str] = []
        quarantined: list[tuple[PurePosixPath, PurePosixPath]] = []
        try:
            for relative, payload in changed_targets.items():
                remote = remote_for(relative)
                temp_remote = remote.with_name(f".{remote.name}.codex-upload-full-{stamp}")
                backup_remote = remote.with_name(f".{remote.name}.codex-backup-full-{stamp}")
                delete_file_optional(ftp, temp_remote)
                delete_file_optional(ftp, backup_remote)
                store_and_verify(ftp, temp_remote, payload)
                # Track the target before the first rename so a failure between
                # the original->backup and temp->original renames is recoverable.
                replaced.append(relative)
                if originals[relative] is not None:
                    ftp.rename(str(remote), str(backup_remote))
                    manifest["targets"][relative]["remote_backup"] = str(backup_remote)
                ftp.rename(str(temp_remote), str(remote))
                write_manifest(backup_dir, manifest)

            for relative, payload in changed_targets.items():
                current = retrieve_optional(ftp, remote_for(relative))
                if current is None or sha256(current) != sha256(payload):
                    raise RuntimeError(f"Final deployment verification failed: {relative}")

            for obsolete_text in OBSOLETE_PATHS:
                obsolete = PurePosixPath(obsolete_text)
                kind = remote_kind(ftp, obsolete)
                if kind is None:
                    manifest["quarantines"].append(
                        {"original": str(obsolete), "quarantine": None, "kind": None}
                    )
                    continue
                quarantine = obsolete.with_name(f".codex-quarantine-{obsolete.name}-{stamp}")
                if remote_kind(ftp, quarantine) is not None:
                    raise RuntimeError(f"Unexpected pre-existing quarantine: {quarantine}")
                ftp.rename(str(obsolete), str(quarantine))
                quarantined.append((obsolete, quarantine))
                manifest["quarantines"].append(
                    {"original": str(obsolete), "quarantine": str(quarantine), "kind": kind}
                )
                write_manifest(backup_dir, manifest)
        except Exception:
            for original_path, quarantine_path in reversed(quarantined):
                if remote_kind(ftp, quarantine_path) is not None:
                    ftp.rename(str(quarantine_path), str(original_path))
            for relative in reversed(replaced):
                remote = remote_for(relative)
                entry = manifest["targets"][relative]
                backup_remote_text = entry.get("remote_backup")
                delete_file_optional(ftp, remote)
                if backup_remote_text:
                    ftp.rename(backup_remote_text, str(remote))
                elif originals[relative] is not None:
                    store_and_verify(ftp, remote, originals[relative])
            manifest["status"] = "rolled_back_after_deployment_error"
            write_manifest(backup_dir, manifest)
            raise

    manifest["status"] = "deployed_quarantined_pending_http_verification"
    manifest["deployed_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(backup_dir, manifest)
    return {
        "mode": "deploy",
        "backup_dir": str(backup_dir),
        "status": manifest["status"],
        **summary,
        "quarantined": sum(1 for item in manifest["quarantines"] if item["quarantine"]),
    }


def rollback(password: str, backup_dir_text: str) -> dict:
    backup_dir, manifest = load_manifest(backup_dir_text)
    with login_ftp(password, timeout=40) as ftp:
        for item in reversed(manifest.get("quarantines", [])):
            if not item.get("quarantine"):
                continue
            original = PurePosixPath(item["original"])
            quarantine = PurePosixPath(item["quarantine"])
            if remote_kind(ftp, quarantine) is not None and remote_kind(ftp, original) is None:
                ftp.rename(str(quarantine), str(original))
        for relative, entry in reversed(list(manifest["targets"].items())):
            if not entry.get("changed", True):
                continue
            remote = remote_for(relative)
            if entry["remote_existed"]:
                payload = Path(entry["rollback_file"]).read_bytes()
                if sha256(payload) != entry["remote_sha256"]:
                    raise RuntimeError(f"Rollback hash mismatch: {relative}")
                store_and_verify(ftp, remote, payload)
            else:
                delete_file_optional(ftp, remote)
        for entry in manifest["targets"].values():
            if entry.get("remote_backup"):
                delete_file_optional(ftp, PurePosixPath(entry["remote_backup"]))
    manifest["status"] = "rolled_back"
    manifest["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(backup_dir, manifest)
    return {"mode": "rollback", "backup_dir": str(backup_dir), "status": manifest["status"]}


def cleanup(password: str, backup_dir_text: str) -> dict:
    backup_dir, manifest = load_manifest(backup_dir_text)
    if manifest.get("status") != "deployed_quarantined_pending_http_verification":
        raise RuntimeError(f"Refusing cleanup for status: {manifest.get('status')}")
    removed_files = 0
    with login_ftp(password, timeout=60) as ftp:
        for item in manifest.get("quarantines", []):
            if item.get("quarantine"):
                removed_files += remove_tree(ftp, PurePosixPath(item["quarantine"]))
        for entry in manifest["targets"].values():
            if entry.get("remote_backup"):
                delete_file_optional(ftp, PurePosixPath(entry["remote_backup"]))
        for item in manifest.get("quarantines", []):
            if item.get("quarantine") and remote_kind(ftp, PurePosixPath(item["quarantine"])) is not None:
                raise RuntimeError(f"Quarantine cleanup failed: {item['quarantine']}")
    manifest["status"] = "deployed_verified_remnants_deleted"
    manifest["cleanup_at"] = datetime.now(timezone.utc).isoformat()
    manifest["removed_files"] = removed_files
    write_manifest(backup_dir, manifest)
    return {
        "mode": "cleanup",
        "backup_dir": str(backup_dir),
        "status": manifest["status"],
        "removed_files": removed_files,
    }


def purge_stale_remnants(password: str) -> dict:
    """Remove only Codex deployment remnants for known release targets.

    Names must match both a known target/obsolete path and the timestamped
    deployment naming convention. This intentionally cannot delete arbitrary
    hidden files or active application content.
    """
    targets, _summary = read_local_targets()
    target_names: dict[PurePosixPath, set[str]] = {}
    for relative in targets:
        remote = remote_for(relative)
        target_names.setdefault(remote.parent, set()).add(remote.name)

    obsolete_names: dict[PurePosixPath, set[str]] = {}
    for obsolete_text in OBSOLETE_PATHS:
        obsolete = PurePosixPath(obsolete_text)
        obsolete_names.setdefault(obsolete.parent, set()).add(obsolete.name)

    stamp = r"\d{8}T\d{6}Z"
    removed_paths: list[str] = []
    removed_files = 0
    directories = sorted(set(target_names) | set(obsolete_names), key=str)
    with login_ftp(password, timeout=60) as ftp:
        for parent in directories:
            try:
                entries = list(ftp.mlsd(str(parent)))
            except ftplib.error_perm as exc:
                if str(exc).startswith("550"):
                    continue
                raise
            for name, facts in entries:
                child = parent / name
                target_match = re.fullmatch(
                    rf"\.(.+)\.codex-(?:upload|backup)(?:-full)?-{stamp}",
                    name,
                )
                is_known_target = bool(
                    target_match
                    and target_match.group(1) in target_names.get(parent, set())
                )
                is_known_quarantine = any(
                    re.fullmatch(
                        rf"\.codex-quarantine-{re.escape(obsolete_name)}-{stamp}",
                        name,
                    )
                    for obsolete_name in obsolete_names.get(parent, set())
                )
                if not (is_known_target or is_known_quarantine):
                    continue
                if facts.get("type") == "dir":
                    removed_files += remove_tree(ftp, child)
                else:
                    delete_file_optional(ftp, child)
                    removed_files += 1
                removed_paths.append(str(child))
    return {
        "mode": "purge-remnants",
        "removed_paths": len(removed_paths),
        "removed_files": removed_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=("inspect", "deploy", "rollback", "cleanup", "purge-remnants"),
    )
    parser.add_argument("--backup-dir")
    args = parser.parse_args()
    if args.mode == "inspect":
        _targets, summary = read_local_targets()
        print(json.dumps({"mode": "inspect", **summary, "obsolete_paths": list(OBSOLETE_PATHS)}, ensure_ascii=False))
        return 0
    password = os.environ.get(PASSWORD_ENV)
    if not password:
        raise RuntimeError(f"{PASSWORD_ENV} is not set")
    if args.mode == "deploy":
        result = deploy(password)
    elif args.mode == "purge-remnants":
        result = purge_stale_remnants(password)
    else:
        if not args.backup_dir:
            raise RuntimeError("--backup-dir is required")
        result = rollback(password, args.backup_dir) if args.mode == "rollback" else cleanup(password, args.backup_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())













