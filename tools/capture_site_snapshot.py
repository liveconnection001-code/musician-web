#!/usr/bin/env python3
"""Capture a compact, review-friendly snapshot of the current working state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP_DIR = ROOT / "default_snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "deploy_company": ROOT / "new_site/deployment/app/View/catalog/cl01_3/default/index.html",
    "deploy_css": ROOT / "new_site/deployment/app/webroot/css/recent_achievements.css",
    "works_template": ROOT / "new_site/works_deployment/app/View/catalog/cl01_2/default/index.html",
    "works_css": ROOT / "new_site/works_deployment/app/webroot/css/works_showcase.css",
    "artist_template": ROOT / "new_site/artist_deployment/app/View/catalog/cl02_4/default/index.html",
    "artist_css": ROOT / "new_site/artist_deployment/app/webroot/css/artist_megumi.css",
    "seo_home": ROOT / "new_site/seo_deployment/app/View/Homes/index.html",
    "seo_meta": ROOT / "new_site/seo_deployment/app/View/Elements/seo_meta.html",
}

MANIFESTS = {
    "seo_manifest": ROOT / "new_site/seo_deployment/seo_manifest.json",
    "works_manifest": ROOT / "new_site/works_deployment/performance_gallery_manifest.json",
    "artist_manifest": ROOT / "new_site/artist_deployment/asset_manifest.json",
}


def digest_file(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    payload = path.read_bytes()
    return {
        "bytes": len(payload),
        "sha256": sha256(payload).hexdigest(),
    }


def image_dir_summary(dir_path: Path) -> dict[str, int]:
    if not dir_path.is_dir():
        return {"files": 0, "bytes": 0}
    total_files = 0
    total_bytes = 0
    for item in dir_path.rglob("*"):
        if item.is_file():
            total_files += 1
            total_bytes += item.stat().st_size
    return {"files": total_files, "bytes": total_bytes}


snapshot = {
    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    "workspace": str(ROOT),
    "defaults": {
        "version": "pre-github-default",
        "notes": "この時点の本番反映前提の現行状態をデフォルト化",
    },
    "target_files": {},
    "manifests": {},
    "image_summary": {},
}

for key, path in TARGETS.items():
    snapshot["target_files"][key] = {
        "path": str(path.relative_to(ROOT)),
        **(digest_file(path) or {}),
    }

for key, path in MANIFESTS.items():
    snapshot["manifests"][key] = {
        "path": str(path.relative_to(ROOT)),
        **(digest_file(path) or {}),
    }

snapshot["image_summary"] = {
    "works_gallery": image_dir_summary(ROOT / "new_site/works_deployment/app/webroot/images/works/gallery"),
    "works_root": image_dir_summary(ROOT / "new_site/works_deployment/app/webroot/images/works"),
    "artist_images": image_dir_summary(ROOT / "new_site/artist_deployment/app/webroot/images/artists"),
}

stamp = datetime.now(timezone.utc).strftime("snapshot-%Y%m%dT%H%M%SZ")
for filename in (f"{stamp}.json", "latest.json"):
    target = SNAP_DIR / filename
    target.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

print(json.dumps({"status": "ok", "snapshot": str(SNAP_DIR / f"{stamp}.json")}, ensure_ascii=False))
