"""Prepare privacy-safe Works images from explicitly selected mobile photos.

The NAS originals are opened read-only. Output files are resized, re-encoded,
and stripped of EXIF/GPS metadata before they enter either preview or release
assets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps


SELECTIONS = (
    {
        "key": "hero-corporate-show",
        "source": "PXL_20260226_092253137.jpg",
        "position": (0.5, 0.46),
    },
    {
        "key": "corporate-party",
        "source": "PXL_20260225_103520631.jpg",
        "position": (0.5, 0.48),
    },
    {
        "key": "international-reception",
        "source": "PXL_20250724_094047556.jpg",
        "position": (0.53, 0.5),
    },
    {
        "key": "japanese-hospitality",
        "source": "PXL_20260130_101350887.jpg",
        "position": (0.5, 0.5),
    },
    {
        "key": "hotel-live",
        "source": "PXL_20250319_105246876.jpg",
        "position": (0.5, 0.5),
    },
    {
        "key": "large-event",
        "source": "PXL_20250330_024327763.jpg",
        "position": (0.5, 0.45),
    },
    {
        "key": "live-streaming",
        "source": "1753510948619.jpg",
        "position": (0.5, 0.5),
    },
)


def save_variants(image: Image.Image, output_dir: Path, key: str, size: tuple[int, int]) -> None:
    prepared = ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=SELECTION_POSITIONS[key],
    )
    prepared.save(output_dir / f"{key}.webp", "WEBP", quality=86, method=6)
    prepared.save(output_dir / f"{key}.jpg", "JPEG", quality=88, optimize=True, progressive=True)


SELECTION_POSITIONS = {item["key"]: item["position"] for item in SELECTIONS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", action="append", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    output_dirs = list(dict.fromkeys(args.output))
    for output_dir in output_dirs:
        output_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, object]] = []
    for selection in SELECTIONS:
        source_path = args.source / str(selection["source"])
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        with Image.open(source_path) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            source_size = image.size
            target_size = (1920, 1080) if selection["key"] == "hero-corporate-show" else (1440, 900)
            for output_dir in output_dirs:
                save_variants(image, output_dir, str(selection["key"]), target_size)

        manifest.append(
            {
                "key": selection["key"],
                "sourceFile": selection["source"],
                "sourcePixels": list(source_size),
                "outputPixels": list(target_size),
                "metadata": "stripped during re-encode",
            }
        )

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps({"photos": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(SELECTIONS)} photos in {len(output_dirs)} output directories")


if __name__ == "__main__":
    main()
