"""Build local contact sheets for Megumi Omachi's supplied promo photos."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def font(size: int) -> ImageFont.ImageFont:
    for path in (Path(r"C:\Windows\Fonts\meiryo.ttc"), Path(r"C:\Windows\Fonts\arial.ttf")):
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    photos = sorted(
        (path for path in args.source.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED),
        key=lambda path: (path.parent.name, path.name),
    )
    args.output.mkdir(parents=True, exist_ok=True)
    columns, rows = 4, 4
    cell_w, image_h, label_h = 360, 300, 66
    margin, gap = 18, 12
    sheet_w = margin * 2 + columns * cell_w + (columns - 1) * gap
    sheet_h = margin * 2 + rows * (image_h + label_h) + (rows - 1) * gap
    text_font = font(16)
    small_font = font(13)
    per_sheet = columns * rows

    manifest = []
    for sheet_index in range((len(photos) + per_sheet - 1) // per_sheet):
        canvas = Image.new("RGB", (sheet_w, sheet_h), "#e9eef5")
        draw = ImageDraw.Draw(canvas)
        chunk = photos[sheet_index * per_sheet:(sheet_index + 1) * per_sheet]
        for item_index, path in enumerate(chunk):
            row, column = divmod(item_index, columns)
            x = margin + column * (cell_w + gap)
            y = margin + row * (image_h + label_h + gap)
            draw.rounded_rectangle(
                (x, y, x + cell_w, y + image_h + label_h),
                radius=8, fill="white", outline="#b7c7da",
            )
            with Image.open(path) as source:
                original = ImageOps.exif_transpose(source).convert("RGB")
                preview = ImageOps.contain(original, (cell_w - 12, image_h - 12), Image.Resampling.LANCZOS)
                canvas.paste(preview, (x + (cell_w - preview.width) // 2, y + (image_h - preview.height) // 2))
                size_text = f"{original.width} x {original.height}"
            label = path.name if len(path.name) <= 36 else path.name[:33] + "..."
            draw.text((x + 10, y + image_h + 5), label, fill="#102d52", font=text_font)
            draw.text((x + 10, y + image_h + 34), f"{path.parent.name} / {size_text}", fill="#60738e", font=small_font)
            manifest.append(f"{sheet_index + 1:02d}-{item_index + 1:02d}\t{path}")
        canvas.save(args.output / f"contact_{sheet_index + 1:02d}.jpg", quality=90, optimize=True)

    (args.output / "manifest.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Built {len(photos)} photos across {(len(photos) + per_sheet - 1) // per_sheet} contact sheets")


if __name__ == "__main__":
    main()
