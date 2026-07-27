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
ACHIEVEMENT_TEMPLATES = (
    ROOT / "new_site" / "deployment" / "app" / "View" / "catalog" / "cl01_3" / "default" / "index.html",
    ROOT / "new_site" / "seo_deployment" / "app" / "View" / "catalog" / "cl01_3" / "default" / "index.html",
)
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
    require(combined.count("(int)$tbl_id === 62 || !empty($tbl_image1)") == 4, "Megumi image gates are incomplete")

    require("youtube-nocookie.com/embed/kZvvnMDZHXU" in detail, "YouTube embed missing")
    require("youtu.be/kZvvnMDZHXU" in detail, "YouTube link missing")
    for url in SNS_URLS:
        require(detail.count(url) >= 2, f"SNS URL missing: {url}")
    require(len(re.findall(r"array\('slug' => '[^']+'", detail)) == 10, "Gallery must contain ten candidates")
    require('data-rel="lightcase:megumi-profile"' in detail, "Click-to-enlarge gallery missing")
    require('aria-label="敦煌杯2025全日本二胡コンクール銀賞の賞状を拡大表示"' in detail, "Award image label missing")
    require(
        'src="/images/megumi-award-certificate-card.jpg?v=20260727"' in detail,
        "Award card image reference is missing or stale",
    )
    require(
        'href="/images/megumi-award-certificate-large.jpg?v=20260727"' in detail,
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
    for path in ACHIEVEMENT_TEMPLATES:
        text = path.read_text(encoding="utf-8")
        for year in expected_years:
            require(
                text.count(f'achievements.html#achievements-{year}') == 1,
                f"Sidebar link mismatch: {path}, {year}",
            )
            require(
                text.count(f'company.html#achievements-{year}') == 0,
                f"Old company anchor remains: {path}, {year}",
            )
            require(text.count(f'id="achievements-{year}"') == 1, f"Year section mismatch: {path}, {year}")
        require(text.count('<details class="achievement-year"') == 8, f"Eight year sections required: {path}")
        require(text.count('<li class="achievement-list__item">') == expected_entries, f"Entry count mismatch: {path}")
        require("2019〜2026年" not in text, f"Grouped year label remains: {path}")
        require("主な実績" not in text, f"Unrequested wording remains: {path}")
        require("achievement-list__date" not in text, f"Month/all-year column remains: {path}")
        require("achievement-year__caption" not in text, f"Redundant year caption remains: {path}")
        require("recent-achievements__intro" not in text, f"Removed intro remains: {path}")
        require("<?php foreach($category_all as $category_id => $category):?>" not in text, f"Old CMS categories remain: {path}")
        require("<?php if (!$isCategoryAll): ?>" not in text, f"Unexpected old category guard remains: {path}")
    css = ACHIEVEMENT_CSS.read_text(encoding="utf-8")
    require("grid-template-columns: 170px minmax(0, 1fr);" in css, "Desktop achievements layout missing")
    require("achievement-list__date" not in css and "recent-achievements__intro" not in css, "Removed achievements CSS remains")
    seo = ACHIEVEMENT_TEMPLATES[1].read_text(encoding="utf-8")
    require("$seoTitle" in seo and "seo_meta" in seo, "Company SEO layer was lost")
    return expected_entries


def main() -> None:
    verify_artist()
    entry_count = verify_achievements()
    print(f"Final release validation passed: Artist text/category/profile/media/SEO checks and 8 achievement years with {entry_count} entries.")


if __name__ == "__main__":
    main()
