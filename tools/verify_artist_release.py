"""Validate the staged Megumi Omachi artist-page release."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "new_site" / "artist_deployment"
ASSETS = RELEASE / "app" / "webroot" / "images" / "artists" / "megumi-omachi"

GALLERY_SLUGS = (
    "portrait",
    "studio-seated",
    "studio-qipao",
    "hangzhou-garden",
    "hangzhou-erhu",
    "white-hydrangea",
    "black-portrait",
    "red-lantern",
    "red-full",
    "stage",
)

SNS_URLS = (
    "https://x.com/MUSICIAN_MEGUMI?s=20",
    "https://www.threads.com/@megmilk323?hl=ja",
    "https://www.instagram.com/megmilk323/",
    "https://www.facebook.com/da.ting.megumi/about",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    detail = (RELEASE / "app/View/catalog/cl02_4/default/view.html").read_text(encoding="utf-8")
    listing = (RELEASE / "app/View/catalog/cl02_4/default/index.html").read_text(encoding="utf-8")
    home = (RELEASE / "app/View/Homes/index.html").read_text(encoding="utf-8")
    css = (RELEASE / "app/webroot/css/artist_megumi.css").read_text(encoding="utf-8")
    combined = "\n".join((detail, listing, home, css))

    require("株式会社MUSICIAN" not in combined, "Prohibited company name found")
    require("株式会社東京アーティスト協会" in detail, "Correct company name missing")
    require("$isMegumiOmachi = ((int)$tbl_id === 62);" in detail, "ID 62 detail override missing")
    require("'seoPageType' => 'ProfilePage'" in detail, "ProfilePage SEO type missing")
    require("'@type' => 'Person'" in detail, "Person structured data missing")
    require("2年間の進修課程を修了" in detail, "Current two-year Shanghai Conservatory completion wording missing")
    require("1年間" not in detail, "Obsolete one-year study wording remains")
    require("$artistId === 62" in listing and "所属アーティスト" in listing, "Affiliation move missing")
    require("(int)$tbl_id === 51" in home and "$tbl_id = 62" in home, "Home slot replacement missing")

    youtube_id = "kZvvnMDZHXU"
    require(f"youtube-nocookie.com/embed/{youtube_id}" in detail, "Requested YouTube embed missing")
    require(f"youtu.be/{youtube_id}" in detail, "Requested YouTube link missing")
    require("megumi-erhu-performance.mp4" not in detail, "Obsolete local video remains in detail")
    require(".megumi-video__frame" in css and ".megumi-video iframe" in css, "Responsive YouTube CSS missing")

    for url in SNS_URLS:
        require(detail.count(url) >= 2, f"SNS URL must appear in hero and official links: {url}")
    require("https://twitter.com/MUSICIAN_MEGUMI" not in detail, "Old X URL remains")

    gallery_count = len(re.findall(r"array\('slug' => '[^']+'", detail))
    require(gallery_count == len(GALLERY_SLUGS), f"Gallery must contain {len(GALLERY_SLUGS)} profile candidates")
    require('data-rel="lightcase:megumi-profile"' in detail, "Click-to-enlarge gallery missing")

    required_files: set[str] = set()
    for slug in GALLERY_SLUGS:
        for variant in ("thumb", "large", "card"):
            for extension in ("jpg", "webp"):
                required_files.add(f"megumi-{slug}-{variant}.{extension}")
    for variant in ("thumb", "large", "card"):
        for extension in ("jpg", "webp"):
            required_files.add(f"megumi-award-certificate-{variant}.{extension}")

    missing = sorted(name for name in required_files if not (ASSETS / name).is_file())
    require(not missing, f"Missing release assets: {missing}")

    obsolete_names = (
        "megumi-erhu-performance.mp4",
        "megumi-erhu-performance-poster.jpg",
        "megumi-erhu-performance-poster.webp",
    )
    require(not any((ASSETS / name).exists() for name in obsolete_names), "Obsolete local video asset remains")

    jpgs = list(ASSETS.glob("*.jpg"))
    require(jpgs, "No JPEG assets found")
    exif_files = []
    for path in jpgs:
        with Image.open(path) as image:
            if len(image.getexif()):
                exif_files.append(path.name)
            require(image.width > 0 and image.height > 0, f"Invalid dimensions: {path.name}")
    require(not exif_files, f"EXIF metadata remains: {exif_files}")

    print(
        "Artist release validation passed: "
        f"{len(GALLERY_SLUGS)} supplied gallery photos, {len(jpgs)} JPEG derivatives, "
        "no EXIF, YouTube/SNS/profile/top/list/detail/SEO checks passed."
    )


if __name__ == "__main__":
    main()