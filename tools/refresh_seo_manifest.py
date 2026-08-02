from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "new_site" / "seo_deployment"
MANIFEST = DEPLOYMENT / "seo_manifest.json"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = []
    for path in sorted(
        path
        for path in DEPLOYMENT.rglob("*")
        if path.is_file() and path != MANIFEST and path.name != "CLAUDE_REVIEW.md"
    ):
        payload = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(DEPLOYMENT).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest["file_count"] = len(files)
    manifest["files"] = files
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"SEO manifest refreshed: {len(files)} files")


if __name__ == "__main__":
    main()
