"""Build local-only contact sheets for reviewing the user's mobile photos.

The source directory is read-only. Images are decoded one at a time and only
small review sheets are written beneath the MUSICIAN workspace.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
HEIF_CONVERTER = Path(
    r"C:\Users\Takashi Miyazaki\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\libheif\libheif\bin\heif-convert.exe"
)
DATE_PATTERNS = (
    re.compile(r"(?:PXL_|IMG_|IMG|DSC_?)(20\d{2})(\d{2})(\d{2})", re.I),
    re.compile(r"\b(20\d{2})[-_](\d{2})[-_](\d{2})\b"),
)
EPOCH_MS_PATTERN = re.compile(r"(?<!\d)(1[5-9]\d{11}|2\d{12})(?!\d)")


def date_from_name(name: str) -> datetime | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(name)
        if match:
            try:
                return datetime(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                    tzinfo=timezone.utc,
                )
            except ValueError:
                pass

    epoch_match = EPOCH_MS_PATTERN.search(name)
    if epoch_match:
        try:
            return datetime.fromtimestamp(
                int(epoch_match.group(1)) / 1000,
                tz=timezone.utc,
            )
        except (OverflowError, OSError, ValueError):
            pass
    return None


def collect_images(
    source: Path,
    year: int,
    month: int | None,
    day: int | None = None,
    fallback_mtime: bool = False,
) -> list[Path]:
    matches: list[tuple[datetime, Path]] = []
    for path in source.iterdir():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        captured = date_from_name(path.name)
        if captured is None and fallback_mtime:
            captured = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if captured is None or captured.year != year:
            continue
        if month is not None and captured.month != month:
            continue
        if day is not None and captured.day != day:
            continue
        matches.append((captured, path))
    matches.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    return [item[1] for item in matches]


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = (
        Path(r"C:\Windows\Fonts\meiryo.ttc"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_sheets(images: list[Path], output: Path, label: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    columns, rows = 5, 4
    cell_width, image_height, label_height = 320, 220, 52
    margin, gutter = 18, 10
    sheet_width = margin * 2 + columns * cell_width + (columns - 1) * gutter
    sheet_height = margin * 2 + rows * (image_height + label_height) + (rows - 1) * gutter
    font = load_font(18)
    small_font = load_font(14)
    per_sheet = columns * rows

    manifest_lines = [f"# {label}", "", f"Candidates: {len(images)}", ""]

    for sheet_index in range((len(images) + per_sheet - 1) // per_sheet):
        canvas = Image.new("RGB", (sheet_width, sheet_height), "#f4f1eb")
        draw = ImageDraw.Draw(canvas)
        chunk = images[sheet_index * per_sheet : (sheet_index + 1) * per_sheet]

        for item_index, path in enumerate(chunk):
            row, column = divmod(item_index, columns)
            x = margin + column * (cell_width + gutter)
            y = margin + row * (image_height + label_height + gutter)
            draw.rounded_rectangle(
                (x, y, x + cell_width, y + image_height + label_height),
                radius=8,
                fill="white",
                outline="#d5d0c6",
                width=1,
            )
            try:
                preview_path = path
                temp_dir = None
                if path.suffix.lower() == ".heic":
                    temp_dir = tempfile.TemporaryDirectory()
                    preview_path = Path(temp_dir.name) / "preview.jpg"
                    subprocess.run(
                        [str(HEIF_CONVERTER), str(path), str(preview_path)],
                        check=True,
                        capture_output=True,
                    )
                try:
                    with Image.open(preview_path) as source_image:
                        source_image = ImageOps.exif_transpose(source_image).convert("RGB")
                        thumb = ImageOps.contain(
                            source_image,
                            (cell_width - 12, image_height - 12),
                            Image.Resampling.LANCZOS,
                        )
                        image_x = x + (cell_width - thumb.width) // 2
                        image_y = y + (image_height - thumb.height) // 2
                        canvas.paste(thumb, (image_x, image_y))
                finally:
                    if temp_dir is not None:
                        temp_dir.cleanup()
            except (OSError, UnidentifiedImageError) as exc:
                draw.text((x + 12, y + 80), "PREVIEW ERROR", fill="#a33", font=font)
                manifest_lines.append(f"- ERROR `{path.name}`: {exc}")

            captured = date_from_name(path.name)
            date_label = captured.strftime("%Y-%m-%d") if captured else "date unknown"
            display_name = path.name
            if len(display_name) > 34:
                display_name = display_name[:31] + "..."
            draw.text((x + 9, y + image_height + 4), display_name, fill="#222", font=small_font)
            draw.text((x + 9, y + image_height + 27), date_label, fill="#6d655a", font=small_font)

        sheet_name = f"contact_{sheet_index + 1:02d}.jpg"
        canvas.save(output / sheet_name, quality=88, optimize=True)
        manifest_lines.append(f"- {sheet_name}: {len(chunk)} images")

    (output / "manifest.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--month", type=int, choices=range(1, 13))
    parser.add_argument("--day", type=int, choices=range(1, 32))
    parser.add_argument(
        "--fallback-mtime",
        action="store_true",
        help="Use file modification time when a filename has no capture date.",
    )
    args = parser.parse_args()

    images = collect_images(
        args.source,
        args.year,
        args.month,
        day=args.day,
        fallback_mtime=args.fallback_mtime,
    )
    month_label = f"-{args.month:02d}" if args.month else ""
    day_label = f"-{args.day:02d}" if args.day else ""
    label = f"Mobile photo review {args.year}{month_label}{day_label}"
    build_sheets(images, args.output, label)
    print(f"Built {len(images)} candidates in {args.output}")


if __name__ == "__main__":
    main()
