"""Synchronize only approved logo-neutral Works assets to public destinations."""

from __future__ import annotations

import filecmp
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "temporary_preview_site/public/images/works"
RELEASE = ROOT / "new_site/works_deployment/app/webroot/images/works"
KEYS = (
    "hero-corporate-show",
    "corporate-party",
    "international-reception",
    "japanese-hospitality",
    "hotel-live",
    "large-event",
    "live-streaming",
)


def assert_clean_only(directory: Path) -> None:
    unsafe = sorted(
        path.name
        for path in directory.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".webp"}
        and "-clean" not in path.stem
    )
    if unsafe:
        raise RuntimeError(
            f"Logo-bearing or unapproved originals must not be public: {unsafe}"
        )


def main() -> None:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    assert_clean_only(RELEASE)

    for key in KEYS:
        for extension in ("jpg", "webp"):
            source = RELEASE / f"{key}-clean.{extension}"
            destination = PREVIEW / source.name
            if not source.is_file():
                raise FileNotFoundError(source)
            if not destination.is_file() or not filecmp.cmp(source, destination, shallow=False):
                shutil.copy2(source, destination)

    assert_clean_only(PREVIEW)
    print("Synchronized 14 approved clean Works assets; no public originals present")


if __name__ == "__main__":
    main()