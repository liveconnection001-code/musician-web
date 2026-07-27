"""Build local-only contact sheets from first frames of Megumi mobile videos."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tmp" / "video_tools"))

import imageio_ffmpeg  # type: ignore
from PIL import Image, ImageDraw, ImageFont, ImageOps


VIDEO_EXTENSIONS = {".mov", ".mp4"}


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (Path(r"C:\Windows\Fonts\meiryo.ttc"), Path(r"C:\Windows\Fonts\arial.ttf")):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def collect_videos(source: Path, year: int) -> list[Path]:
    videos = [
        path
        for path in source.iterdir()
        if path.is_file()
        and path.suffix.lower() in VIDEO_EXTENSIONS
        and datetime.fromtimestamp(path.stat().st_mtime).year == year
    ]
    videos.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    return videos


def extract_frame(video: Path, output: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        "1",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        "scale=620:-2",
        "-q:v",
        "3",
        "-y",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, timeout=90)


def build_sheets(videos: list[Path], output: Path, year: int) -> None:
    output.mkdir(parents=True, exist_ok=True)
    columns, rows = 5, 4
    cell_width, image_height, label_height = 320, 220, 54
    margin, gutter = 18, 10
    sheet_width = margin * 2 + columns * cell_width + (columns - 1) * gutter
    sheet_height = margin * 2 + rows * (image_height + label_height) + (rows - 1) * gutter
    font = load_font(14)
    per_sheet = columns * rows
    manifest = [f"# Megumi video review {year}", "", f"Videos: {len(videos)}", ""]

    with tempfile.TemporaryDirectory() as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        for sheet_index in range((len(videos) + per_sheet - 1) // per_sheet):
            canvas = Image.new("RGB", (sheet_width, sheet_height), "#f4f1eb")
            draw = ImageDraw.Draw(canvas)
            chunk = videos[sheet_index * per_sheet : (sheet_index + 1) * per_sheet]
            for item_index, video in enumerate(chunk):
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
                frame = temp_dir / f"frame_{sheet_index}_{item_index}.jpg"
                try:
                    extract_frame(video, frame)
                    with Image.open(frame) as source_image:
                        source_image = ImageOps.exif_transpose(source_image).convert("RGB")
                        thumb = ImageOps.contain(
                            source_image,
                            (cell_width - 12, image_height - 12),
                            Image.Resampling.LANCZOS,
                        )
                        canvas.paste(
                            thumb,
                            (x + (cell_width - thumb.width) // 2, y + (image_height - thumb.height) // 2),
                        )
                except (OSError, subprocess.SubprocessError) as exc:
                    draw.text((x + 12, y + 80), "PREVIEW ERROR", fill="#a33", font=font)
                    manifest.append(f"- ERROR `{video.name}`: {exc}")
                captured = datetime.fromtimestamp(video.stat().st_mtime)
                display_name = video.name if len(video.name) <= 34 else video.name[:31] + "..."
                draw.text((x + 9, y + image_height + 4), display_name, fill="#222", font=font)
                draw.text(
                    (x + 9, y + image_height + 28),
                    captured.strftime("%Y-%m-%d %H:%M"),
                    fill="#6d655a",
                    font=font,
                )
            sheet_name = f"contact_{sheet_index + 1:02d}.jpg"
            canvas.save(output / sheet_name, quality=88, optimize=True)
            manifest.append(f"- {sheet_name}: {len(chunk)} videos")

    (output / "manifest.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--year", required=True, type=int)
    args = parser.parse_args()
    videos = collect_videos(args.source, args.year)
    build_sheets(videos, args.output, args.year)
    print(f"Built {len(videos)} video candidates in {args.output}")


if __name__ == "__main__":
    main()
