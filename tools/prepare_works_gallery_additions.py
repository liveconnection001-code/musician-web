"""Build the approved 2026-07-30 Works gallery additions.

The edited source masters are kept in the Works deployment package. Public
derivatives are re-encoded without EXIF metadata and synchronized to the
production package, local preview, and release-staging mirror.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "new_site/works_deployment/source_overrides"
OUTPUTS = (
    ROOT / "new_site/works_deployment/app/webroot/images/works/gallery",
    ROOT / "temporary_preview_site/public/images/works/gallery",
    ROOT / "work/release_upload/5_works_gallery/app/webroot/images/works/gallery",
)

PHOTOS = (
    {
        "key": "traditional-taiko-ceremony",
        "source": "traditional-taiko-ceremony-clean.png",
        "center": (0.50, 0.50),
    },
    {
        "key": "traditional-shamisen-tatami",
        "source": "traditional-shamisen-tatami-clean.png",
        "center": (0.56, 0.50),
    },
    {
        "key": "jazz-female-big-band-stage",
        "source": "jazz-female-big-band-stage-clean.png",
        "center": (0.50, 0.50),
    },
    {
        "key": "traditional-mariachi-festive",
        "source": "traditional-mariachi-festive-clean.png",
        "center": (0.50, 0.50),
    },
)


def largest_four_by_three(image: Image.Image, center: tuple[float, float]) -> Image.Image:
    """Return a performer-safe 4:3 large image no bigger than 1600x1200."""
    width = min(1600, image.width, int(image.height * 4 / 3))
    width -= width % 4
    height = width * 3 // 4
    return ImageOps.fit(
        image,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=center,
    )


def save_variants(image: Image.Image, output: Path, key: str, center: tuple[float, float]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    card = ImageOps.fit(
        image,
        (960, 720),
        method=Image.Resampling.LANCZOS,
        centering=center,
    )
    small = card.resize((480, 360), Image.Resampling.LANCZOS)
    large = largest_four_by_three(image, center)

    small.save(output / f"{key}-small.webp", "WEBP", quality=82, method=6)
    card.save(output / f"{key}-card.webp", "WEBP", quality=84, method=6)
    card.save(output / f"{key}-card.jpg", "JPEG", quality=87, optimize=True, progressive=True)
    large.save(output / f"{key}-large.jpg", "JPEG", quality=89, optimize=True, progressive=True)


def main() -> None:
    for photo in PHOTOS:
        source = SOURCE / photo["source"]
        if not source.is_file():
            raise FileNotFoundError(source)
        with Image.open(source) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
            for output in OUTPUTS:
                save_variants(image, output, photo["key"], photo["center"])

    print(f"Prepared {len(PHOTOS)} Works gallery additions in {len(OUTPUTS)} destinations")


if __name__ == "__main__":
    main()
