"""Prepare privacy-safe web assets for Megumi Omachi's artist page.

The NAS source is treated as read-only. Published derivatives are resized,
re-encoded without EXIF/GPS metadata, and written to one or more output roots.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps


HEIF_CONVERTER = Path(
    r"C:\Users\Takashi Miyazaki\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\libheif\libheif\bin\heif-convert.exe"
)
FFMPEG = Path(
    r"A:\AI\Web\MUSICIAN\tmp\video_tools\imageio_ffmpeg\binaries"
    r"\ffmpeg-win-x86_64-v7.1.exe"
)

PHOTOS = (
    ("portrait", r"上海スタジオ\0D4A4679.jpg", "二胡を手にした大町めぐみのスタジオポートレート"),
    ("studio-seated", r"上海スタジオ\0D4A4652.jpg", "二胡とともに座る大町めぐみのスタジオ写真"),
    ("studio-qipao", r"上海スタジオ\0D4A4755.jpg", "緑のチャイナドレスで二胡を持つ大町めぐみ"),
    ("hangzhou-garden", r"杭州\20250608_075124780_iOS.jpg", "杭州の庭園に立つ大町めぐみ"),
    ("hangzhou-erhu", r"杭州\20250608_075810310_iOS.jpg", "杭州の庭園で二胡を演奏する大町めぐみ"),
    ("white-hydrangea", r"過去写真\220620_megumi_00103.tif", "紫陽花と白い衣装で二胡を持つ大町めぐみ"),
    ("black-portrait", r"過去写真\220620_megumi_00967arr.jpg", "黒い衣装で二胡を持つ大町めぐみ"),
    ("red-lantern", r"過去写真\220620_megumi_01667.tif", "赤いチャイナドレスで二胡を持つ大町めぐみ"),
    ("red-full", r"過去写真\220620_megumi_01683.tif", "赤い提灯の街並みに立つ大町めぐみ"),
    ("stage", r"過去写真\FRA20221122_00675.jpg", "コンサートで二胡を演奏する大町めぐみ"),
)


def open_source(path: Path) -> Image.Image:
    if path.suffix.lower() != ".heic":
        with Image.open(path) as source:
            return ImageOps.exif_transpose(source).convert("RGB")
    if not HEIF_CONVERTER.exists():
        raise FileNotFoundError(f"HEIC converter not found: {HEIF_CONVERTER}")
    with tempfile.TemporaryDirectory() as temp_dir:
        converted = Path(temp_dir) / "source.jpg"
        subprocess.run(
            [str(HEIF_CONVERTER), str(path), str(converted)],
            check=True,
            capture_output=True,
        )
        with Image.open(converted) as source:
            return ImageOps.exif_transpose(source).convert("RGB")


def contain(image: Image.Image, limit: int) -> Image.Image:
    result = image.copy()
    result.thumbnail((limit, limit), Image.Resampling.LANCZOS)
    return result


def cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.42),
    )


def save_pair(image: Image.Image, stem: Path, jpeg_quality: int = 87) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    image.save(stem.with_suffix(".jpg"), "JPEG", quality=jpeg_quality, optimize=True)
    image.save(stem.with_suffix(".webp"), "WEBP", quality=82, method=6)


def prepare_photo(source: Path, output: Path, slug: str) -> dict[str, object]:
    image = open_source(source)
    large = contain(image, 2000)
    thumb = cover(image, (640, 760))
    card = cover(image, (900, 620))
    save_pair(large, output / f"megumi-{slug}-large")
    save_pair(thumb, output / f"megumi-{slug}-thumb")
    save_pair(card, output / f"megumi-{slug}-card")
    return {
        "source": source.name,
        "slug": slug,
        "original_size": list(image.size),
        "large_size": list(large.size),
        "metadata": "stripped by re-encoding",
    }


def prepare_video(source: Path, output: Path) -> dict[str, object]:
    if not FFMPEG.exists():
        raise FileNotFoundError(f"ffmpeg not found: {FFMPEG}")
    video_output = output / "megumi-erhu-performance.mp4"
    poster_output = output / "megumi-erhu-performance-poster.jpg"
    subprocess.run(
        [
            str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source), "-map", "0:v:0", "-map", "0:a:0",
            "-c", "copy", "-map_metadata", "-1", "-map_chapters", "-1",
            "-movflags", "+faststart", str(video_output),
        ],
        check=True,
    )
    subprocess.run(
        [
            str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
            "-ss", "48", "-i", str(source), "-frames:v", "1",
            "-vf", "scale=1136:640:flags=lanczos", "-map_metadata", "-1",
            str(poster_output),
        ],
        check=True,
    )
    with Image.open(poster_output) as poster:
        clean = poster.convert("RGB")
        clean.save(poster_output, "JPEG", quality=88, optimize=True)
        clean.save(output / "megumi-erhu-performance-poster.webp", "WEBP", quality=82, method=6)
    return {
        "source": source.name,
        "output": video_output.name,
        "metadata": "GPS and container metadata stripped; video/audio streams copied",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, action="append", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    primary = args.output[0]
    primary.mkdir(parents=True, exist_ok=True)
    records = []
    for slug, filename, alt in PHOTOS:
        source = args.source / filename
        if not source.exists():
            raise FileNotFoundError(source)
        record = prepare_photo(source, primary, slug)
        record["alt"] = alt
        records.append(record)
    for mirror in args.output[1:]:
        mirror.mkdir(parents=True, exist_ok=True)
        for slug, _, _ in PHOTOS:
            for variant in ("large", "thumb", "card"):
                for extension in ("jpg", "webp"):
                    name = f"megumi-{slug}-{variant}.{extension}"
                    shutil.copy2(primary / name, mirror / name)

    manifest = {
        "photos": records,
        "video": {
            "type": "youtube",
            "url": "https://youtu.be/kZvvnMDZHXU?si=pn71GfEo_R7wyUXJ",
            "embed": "https://www.youtube-nocookie.com/embed/kZvvnMDZHXU?rel=0",
        },
        "outputs": [str(path) for path in args.output],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(records)} photos and YouTube metadata in {len(args.output)} output roots")


if __name__ == "__main__":
    main()
