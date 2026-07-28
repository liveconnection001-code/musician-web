"""Validate the staged Artist release and achievements relayout."""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ARTIST = ROOT / "new_site" / "artist_deployment"
ASSETS = ARTIST / "app" / "webroot" / "images" / "artists" / "megumi-omachi"
DATA = ROOT / "new_site" / "data" / "achievements_recent.json"
ACHIEVEMENTS_PAGE = ROOT / "new_site" / "seo_deployment" / "app" / "webroot" / "achievements.html"
ACHIEVEMENT_CSS = ROOT / "new_site" / "deployment" / "app" / "webroot" / "css" / "recent_achievements.css"

GALLERY_SLUGS = (
    "portrait", "studio-seated", "studio-qipao", "hangzhou-garden",
    "hangzhou-erhu", "white-hydrangea", "black-portrait",
    "red-lantern", "red-full", "stage",
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


def verify_artist() -> None:
    detail = (ARTIST / "app/View/catalog/cl02_4/default/view.html").read_text(encoding="utf-8")
    listing = (ARTIST / "app/View/catalog/cl02_4/default/index.html").read_text(encoding="utf-8")
    home = (ARTIST / "app/View/Homes/index.html").read_text(encoding="utf-8")
    css = (ARTIST / "app/webroot/css/artist_megumi.css").read_text(encoding="utf-8")
    combined = "\n".join((detail, listing, home, css))

    require("株式会社MUSICIAN" not in combined, "Prohibited company name found")
    require("株式会社東京アーティスト協会" in detail, "Correct company name missing")
    require("2年間の進修課程を修了" in detail and "1年間" not in detail, "Two-year Shanghai completion wording mismatch")
    require("$artistId === 62" in listing and "所属アーティスト" in listing, "Affiliation move missing")
    require("$boxes = array_merge($affiliatedBoxes, $otherBoxes);" in listing, "Existing Artist categories are not preserved")
    require("$artistBox['CatalogBox']['title'] = '大町 めぐみ';" in listing, "Megumi list name text missing")
    require("$artistBox['CatalogBox']['word1'] = 'オオマチ メグミ';" in listing, "Megumi kana text missing")
    require('<p><?php echo $tbl_title; ?></p>' in listing, "Artist names must remain selectable HTML text")
    require('<p class="sub"><?php echo $tbl_word1; ?></p>' in listing, "Artist kana must remain selectable HTML text")
    require('css/artist_megumi.css' in listing, "Artist list alignment stylesheet missing")
    require('.artist_box .box .text{text-align:center}' in css, "Artist name and kana are not centered")
    require('.artist_box .box .text p{user-select:text}' in css, "Artist text selection rule missing")
    require("(int)$tbl_id === 51" in home and "$tbl_id = 62" in home, "Home slot replacement missing")
    require("$tbl_title = '大町 めぐみ';" in home, "Home Megumi name text missing")
    image_gates = re.findall(
        r"\(int\)\$tbl_id === 62(?: \|\| \(int\)\$tbl_id === -101)? \|\| !empty\(\$tbl_image1\)",
        combined,
    )
    require(len(image_gates) == 4, "Megumi image gates are incomplete")

    require("youtube-nocookie.com/embed/kZvvnMDZHXU" in detail, "YouTube embed missing")
    require("youtu.be/kZvvnMDZHXU" in detail, "YouTube link missing")
    for url in SNS_URLS:
        require(detail.count(url) >= 2, f"SNS URL missing: {url}")
    require(len(re.findall(r"array\('slug' => '[^']+'", detail)) == 10, "Gallery must contain ten candidates")
    require('data-rel="lightcase:megumi-profile"' in detail, "Click-to-enlarge gallery missing")
    require('aria-label="敦煌杯2025全日本二胡コンクール銀賞の賞状を拡大表示"' in detail, "Award image label missing")
    require(
        'src="/images/megumi-award-certificate-card.jpg?v=20260728c"' in detail,
        "Award card image reference is missing or stale",
    )
    require(
        'href="/images/megumi-award-certificate-large.jpg?v=20260728c"' in detail,
        "Award enlargement reference is missing or stale",
    )
    require(detail.count("<?php if (!$isMegumiOmachi): ?>") >= 3, "Legacy gallery/modal guards are incomplete")
    require("'seoPageType' => 'ProfilePage'" in detail and "'@type' => 'Person'" in detail, "Profile SEO missing")

    required_files = {
        f"megumi-{slug}-{variant}.{extension}"
        for slug in (*GALLERY_SLUGS, "award-certificate")
        for variant in ("thumb", "large", "card")
        for extension in ("jpg", "webp")
    }
    require(not [name for name in required_files if not (ASSETS / name).is_file()], "Artist image derivatives missing")
    jpgs = list(ASSETS.glob("*.jpg"))
    for path in jpgs:
        with Image.open(path) as image:
            require(not image.getexif(), f"EXIF remains: {path.name}")


def verify_achievements() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    expected_years = [str(year) for year in range(2026, 2018, -1)]
    expected_entries = sum(len(year["entries"]) for year in data["years"])
    text = ACHIEVEMENTS_PAGE.read_text(encoding="utf-8")
    for year in expected_years:
        require(text.count(f'href="#achievements-{year}"') == 1, f"Sidebar link mismatch: {year}")
        require(text.count(f'id="achievements-{year}"') == 1, f"Year section mismatch: {year}")
    require(
        len(re.findall(r'<details class="achievement-year(?: achievement-year--archive)?"', text)) == 21,
        "Twenty-one year sections required",
    )
    require(text.count('class="achievement-category-group__item"') == expected_entries, "Recent entry count mismatch")
    require("2019〜2026年" not in text, "Grouped year label remains")
    require("主な実績" not in text, "Unrequested wording remains")
    require("achievement-list__date" not in text, "Month/all-year column remains")
    require("achievement-year__caption" not in text, "Redundant year caption remains")
    require("recent-achievements__intro" not in text, "Removed intro remains")
    css = ACHIEVEMENT_CSS.read_text(encoding="utf-8")
    require(
        "grid-template-columns: 140px minmax(0, 1fr);" in css
        and ".achievement-category-group" in css,
        "Grouped desktop achievements layout missing",
    )
    require("achievement-list__date" not in css and "recent-achievements__intro" not in css, "Removed achievements CSS remains")
    require("seo_meta" in text and "'seoCanonicalPath' => '/achievements.html'" in text, "Achievements SEO layer was lost")
    return expected_entries


def main() -> None:
    verify_artist()
    entry_count = verify_achievements()
    print(f"Final release validation passed: Artist text/category/profile/media/SEO checks and 8 achievement years with {entry_count} entries.")


if __name__ == "__main__":
    main()
