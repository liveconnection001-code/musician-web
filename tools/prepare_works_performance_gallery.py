"""Prepare the approved historical performance gallery for Works.

The NAS originals are read-only. Every public derivative is EXIF-free,
re-encoded, and resized for either the gallery grid or its enlarged view.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]


PHOTOS = (
    {"key": "unit-live-band", "folder": "unit", "file": "IMG_7570.JPG", "center": (0.50, 0.54), "override": "new_site/works_deployment/source_overrides/unit-live-band-4x3-clean.png"},
    {"key": "unit-modern-trio", "folder": "unit", "file": "879.jpg", "center": (0.50, 0.54), "override": "new_site/works_deployment/source_overrides/unit-modern-trio-centered-clean.png"},
    {"key": "unit-big-band", "folder": "unit", "file": "DSC02749.JPG", "center": (0.52, 0.52), "override": "new_site/works_deployment/source_overrides/unit-big-band-identifiers-removed.png"},
    {"key": "unit-brass-quintet", "folder": "unit", "file": "IMG_8699.JPG", "center": (0.55, 0.54)},
    {"key": "unit-christmas", "folder": "unit", "file": "DSC02211.JPG", "center": (0.50, 0.54), "override": "new_site/works_deployment/source_overrides/unit-christmas-4x3.png"},
    {"key": "unit-electric-strings", "folder": "unit", "file": "20100602_06.jpg", "center": (0.54, 0.50)},
    {"key": "unit-concert-production", "folder": "unit", "file": "DSC00498.JPG", "center": (0.50, 0.61)},
    {"key": "traditional-koto-gala", "folder": "unit", "file": "P1000283.JPG", "center": (0.50, 0.58), "trim": (512, 700, 512, 68)},
    {"key": "unit-kimono", "folder": "unit", "file": "S__3727427.jpg", "center": (0.42, 0.51), "trim": (0, 0, 380, 0)},
    {"key": "unit-outdoor-night", "folder": "unit", "file": "S__2547734.jpg", "center": (0.50, 0.54), "override": "new_site/works_deployment/source_overrides/unit-outdoor-night-clean.png"},
    {"key": "unit-vocal-balcony", "folder": "unit", "file": "Photo002.jpg", "center": (0.54, 0.47)},
    {"key": "traditional-taiko", "folder": "traditional", "file": "DSC_0945.JPG", "center": (0.53, 0.52), "override": "new_site/works_deployment/source_overrides/traditional-taiko-logo-removed.png"},
    {"key": "traditional-japanese-fusion", "folder": "traditional", "file": "DSC00319.JPG", "center": (0.54, 0.54), "trim": (250, 100, 0, 87), "override": "new_site/works_deployment/source_overrides/traditional-japanese-fusion-clean.png"},
    {"key": "traditional-koto-quartet", "folder": "traditional", "file": "DSC01855.JPG", "center": (0.54, 0.53)},
    {"key": "traditional-koto-duo", "folder": "traditional", "file": "DSC01838.JPG", "center": (0.54, 0.54)},
    {"key": "traditional-shamisen-solo", "folder": "traditional", "file": "P1090101.JPG", "center": (0.48, 0.50)},
    {"key": "traditional-flamenco", "folder": "traditional", "file": "DSC01788.JPG", "center": (0.56, 0.50)},
    {"key": "traditional-japanese-dance", "folder": "traditional", "file": "IMG_1657.JPG", "center": (0.50, 0.55), "override": "new_site/works_deployment/source_overrides/traditional-japanese-dance-4x3.png"},
    {"key": "traditional-gospel", "folder": "traditional", "file": "P1030626.JPG", "center": (0.50, 0.55)},
    {"key": "traditional-vocal-show", "folder": "traditional", "file": "PICT0010.JPG", "center": (0.55, 0.52)},
    {"key": "jazz-church-concert", "folder": "JAZZ.POPS", "file": "2.JPG", "center": (0.50, 0.55)},
    {"key": "jazz-quartet", "folder": "JAZZ.POPS", "file": "2008122017040001.jpg", "center": (0.51, 0.52), "redactions": ({"points": ((400, 202), (454, 202), (454, 258), (400, 258)), "fill": (37, 43, 42)},)},
    {"key": "jazz-big-band-concert", "folder": "JAZZ.POPS", "file": "画像 086.jpg", "center": (0.50, 0.50)},
    {"key": "pops-string-live", "folder": "JAZZ.POPS", "file": "20140201_160706.jpg", "center": (0.50, 0.50)},
    {"key": "pops-erhu-piano", "folder": "JAZZ.POPS", "file": "IMG_6565.JPG", "center": (0.50, 0.56)},
    {"key": "classic-orchestra", "folder": "classic", "file": "20110429070.jpg", "center": (0.50, 0.62)},
    {"key": "classic-public-concert", "folder": "classic", "file": "DSC02348.JPG", "center": (0.48, 0.58)},
    {"key": "classic-cruise-brass", "folder": "classic", "file": "ぱしふぃっくびぃなす_190204_0040.jpg", "center": (0.50, 0.42)},
    {"key": "classic-string-ensemble", "folder": "classic", "file": "画像 016.jpg", "center": (0.56, 0.50)},
    {"key": "classic-film-production", "folder": "classic", "file": "画像 022.jpg", "center": (0.58, 0.54)},
    {"key": "classic-mariachi-trio", "folder": "classic", "file": "DSC03285.JPG", "center": (0.50, 0.52), "override": "new_site/works_deployment/source_overrides/classic-mariachi-trio-clean.png"},
    {"key": "classic-gallery-trio", "folder": "classic", "file": "PICT0021.JPG", "center": (0.50, 0.56), "trim": (40, 80, 0, 0)},
    {"key": "concert-opera-scene", "folder": "コンサート制作実績/鈴木慶江/2022_09_24鈴木慶江デビュー20周年/20220924鈴木慶江デビュー20周年記念オーケストラコンサート/公演写真/深谷さん撮影", "file": "_FY20422.jpg", "center": (0.50, 0.52), "override": "//192.168.1.2/Public/MUSICIAN/コンサート制作実績/鈴木慶江/2022_09_24鈴木慶江デビュー20周年/20220924鈴木慶江デビュー20周年記念オーケストラコンサート/公演写真/深谷さん撮影/_FY20422.jpg"},
    {"key": "concert-operatic-heroines", "folder": "コンサート制作実績/鈴木慶江/2022_09_24鈴木慶江デビュー20周年/20220924鈴木慶江デビュー20周年記念オーケストラコンサート/公演写真/深谷さん撮影", "file": "_FY20745.jpg", "center": (0.52, 0.50), "override": "//192.168.1.2/Public/MUSICIAN/コンサート制作実績/鈴木慶江/2022_09_24鈴木慶江デビュー20周年/20220924鈴木慶江デビュー20周年記念オーケストラコンサート/公演写真/深谷さん撮影/_FY20745.jpg"},
    {"key": "concert-orchestra-amber", "folder": "コンサート制作実績/鈴木慶江/2022_09_24鈴木慶江デビュー20周年/20220924鈴木慶江デビュー20周年記念オーケストラコンサート/公演写真/深谷さん撮影", "file": "_FY30064.jpg", "center": (0.49, 0.55), "override": "//192.168.1.2/Public/MUSICIAN/コンサート制作実績/鈴木慶江/2022_09_24鈴木慶江デビュー20周年/20220924鈴木慶江デビュー20周年記念オーケストラコンサート/公演写真/深谷さん撮影/_FY30064.jpg"},
    {"key": "concert-soprano-stage", "folder": "コンサート制作実績/鈴木慶江/写真2018年6月オペラティックヒロインズ", "file": "S__57876567.jpg", "center": (0.50, 0.50), "override": "//192.168.1.2/Public/MUSICIAN/コンサート制作実績/鈴木慶江/写真2018年6月オペラティックヒロインズ/S__57876567.jpg"},
)


def apply_trim(image: Image.Image, trim: tuple[int, int, int, int] | None) -> Image.Image:
    if not trim:
        return image
    left, top, right, bottom = trim
    return image.crop((left, top, image.width - right, image.height - bottom))


def apply_redactions(image: Image.Image, redactions: tuple[dict, ...] | None) -> Image.Image:
    """Blend client/event identifiers into their surrounding display surface."""
    if not redactions:
        return image
    result = image.copy()
    for redaction in redactions:
        mask = Image.new("L", result.size, 0)
        ImageDraw.Draw(mask).polygon(redaction["points"], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(5))
        neutral = Image.new("RGB", result.size, tuple(redaction["fill"]))
        result = Image.composite(neutral, result, mask)
    return result


def save_variants(image: Image.Image, output_dir: Path, key: str, center: tuple[float, float]) -> dict[str, list[int]]:
    card_size = (960, 720)
    # The approved grid is full-bleed 4:3. Per-photo centering keeps performers
    # in view; portrait sources that would need excessive cropping use a 4:3
    # project-bound override prepared from the original photograph.
    card = ImageOps.fit(image, card_size, method=Image.Resampling.LANCZOS, centering=center)
    small = card.resize((480, 360), Image.Resampling.LANCZOS)
    small.save(output_dir / f"{key}-small.webp", "WEBP", quality=82, method=6)
    card.save(output_dir / f"{key}-card.webp", "WEBP", quality=84, method=6)
    card.save(output_dir / f"{key}-card.jpg", "JPEG", quality=87, optimize=True, progressive=True)

    large = image.copy()
    large.thumbnail((1920, 1600), Image.Resampling.LANCZOS)
    large.save(output_dir / f"{key}-large.jpg", "JPEG", quality=89, optimize=True, progressive=True)
    return {"smallPixels": list(small.size), "cardPixels": list(card.size), "largePixels": list(large.size)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", action="append", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    output_dirs = list(dict.fromkeys(args.output))
    for output_dir in output_dirs:
        output_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for photo in PHOTOS:
        source_override = photo.get("override")
        source_path = (
            PROJECT_ROOT / str(source_override)
            if source_override
            else args.source / str(photo["folder"]) / str(photo["file"])
        )
        if not source_path.is_file():
            raise FileNotFoundError(source_path)

        with Image.open(source_path) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            source_size = image.size
            image = apply_trim(image, photo.get("trim"))
            image = apply_redactions(image, photo.get("redactions"))
            output_sizes = None
            for output_dir in output_dirs:
                output_sizes = save_variants(image, output_dir, str(photo["key"]), photo["center"])

        manifest.append({
            "key": photo["key"],
            "sourceFolder": str(Path(str(source_override)).parent) if source_override else photo["folder"],
            "sourceFile": Path(str(source_override)).name if source_override else photo["file"],
            "sourcePixels": list(source_size),
            "redactions": len(photo.get("redactions", ())),
            **(output_sizes or {}),
            "metadata": "stripped during re-encode",
        })

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps({"photos": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(manifest)} performance photos in {len(output_dirs)} output directories")


if __name__ == "__main__":
    main()
