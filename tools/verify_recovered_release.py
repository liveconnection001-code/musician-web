#!/usr/bin/env python3
"""Strict validation for the approved 2026-07-28 MUSICIAN release."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SEO = ROOT / "new_site/seo_deployment"
ARTIST = ROOT / "new_site/artist_deployment"
WORKS = ROOT / "new_site/works_deployment"
COMPANY = SEO / "app/View/catalog/cl01_3/default/index.html"
ACHIEVEMENTS = SEO / "app/webroot/achievements.html"
STYLE = SEO / "app/webroot/css/style.css"
ACHIEVEMENTS_CSS = ROOT / "new_site/deployment/app/webroot/css/recent_achievements.css"
RECOVERED = ROOT / "work/recovered_achievements_2006_2018.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_shared_headers() -> None:
    files = {
        "Business": SEO / "app/webroot/business.html",
        "Artist": ARTIST / "app/View/catalog/cl02_4/default/index.html",
        "Artist detail": ARTIST / "app/View/catalog/cl02_4/default/view.html",
        "About us": COMPANY,
        "Achievements": ACHIEVEMENTS,
    }
    for label, path in files.items():
        text = path.read_text(encoding="utf-8")
        require(text.count("<header>") == 1, f"{label}: header count")
        require(text.count("<footer>") == 1, f"{label}: footer count")
        require(text.count('id="midashi_h2"') == 1, f"{label}: shared heading missing")
        require("style.css?v=20260728b" in text, f"{label}: CSS cache key missing")
    css = STYLE.read_text(encoding="utf-8")
    require("approved shared page heading" in css, "Approved heading CSS missing")
    require(re.search(r"#midashi_h2\s*\{[^}]*height:\s*40px", css, re.S), "Navy band is not 40px")
    require("@media screen and (max-width: 767px)" in css, "Mobile heading rules missing")


def validate_about() -> None:
    text = COMPANY.read_text(encoding="utf-8")
    megumi = text.index("代表取締役</span> 大町めぐみ")
    miyazaki = text.index("プロデューサー</span> 宮﨑 隆")
    require(megumi < miyazaki, "About us profile order is wrong")
    require("company_photo_megumi.jpg?v=20260728b" in text, "Megumi About image cache key missing")
    require("company_photo_miyazaki_illustration.jpg?v=20260728b" in text, "Miyazaki illustration cache key missing")
    require("recent-achievements" not in text and 'id="achievements"' not in text, "Achievements remain in About us")
    require("Career" not in text, "Removed Career section remains")
    require(text.count("<span>About us</span>私たちについて") == 1, "About us title is duplicated")

    deployed = WORKS / "app/webroot/images"
    require(
        sha256(deployed / "company_photo_megumi.jpg")
        == sha256(ROOT / "work/release_upload/4_achievements/images/company_photo_megumi.jpg"),
        "Megumi About image differs from approved asset",
    )
    require(
        sha256(deployed / "company_photo_miyazaki_illustration.jpg")
        == sha256(ROOT / "work/approved_assets/miyazaki_portrait_illustration.jpg"),
        "Miyazaki illustration differs from approved asset",
    )


def validate_achievements() -> None:
    text = ACHIEVEMENTS.read_text(encoding="utf-8")
    years = list(range(2026, 2005, -1))
    ids = [int(value) for value in re.findall(r'id="achievements-(\d{4})"', text)]
    links = [int(value) for value in re.findall(r'href="#achievements-(\d{4})"', text)]
    require(ids == years, f"Achievements IDs mismatch: {ids}")
    require(links == years, f"Achievements Category mismatch: {links}")
    require(text.count('class="achievement-category-group__item"') == 85, "Recent achievement item count changed")
    require('class="achievement-category-group"' in text, "Recent achievements are not grouped by category")
    require(not re.search(r'<details class="achievement-year"[^>]*\sopen(?:\s|>)', text), "A year is open by default")
    require("ISEKI Global Awards</span><span class=\"achievement-list__detail\">ソプラノ歌唱の出演手配" in text, "Achievement title/detail are not kept inline")
    require("recent_achievements.css?v=20260728b" in text, "Achievements CSS missing")
    require("seoCanonicalPath' => '/achievements.html'" in text, "Achievements canonical missing")
    require("2006年から2026年" in text, "Achievements description does not cover full archive")

    recovered = {int(item["year"]): item for item in json.loads(RECOVERED.read_text(encoding="utf-8"))}
    require(set(recovered) == set(range(2006, 2019)), "Recovered years incomplete")
    for year, item in recovered.items():
        require(item["html"] in text, f"Recovered {year} content changed")

    css = ACHIEVEMENTS_CSS.read_text(encoding="utf-8")
    require("grid-template-columns: minmax(0, 1fr) 180px" in css, "Category width is not 180px")
    require("position: sticky" in css and "align-self: stretch" in css, "Sticky Category is incomplete")
    require(".achievements-category a::before" in css, "CSS year arrow missing")
    require("grid-template-columns: repeat(3, 1fr)" in css, "Mobile Category layout missing")
    require(".achievement-list__line" in css and "display: flex" in css, "Inline achievement layout missing")


def validate_artist() -> None:
    listing = (ARTIST / "app/View/catalog/cl02_4/default/index.html").read_text(encoding="utf-8")
    detail = (ARTIST / "app/View/catalog/cl02_4/default/view.html").read_text(encoding="utf-8")
    home = (ARTIST / "app/View/Homes/index.html").read_text(encoding="utf-8")
    require("$artistId === 62" in listing and "所属アーティスト" in listing, "Megumi affiliation is missing")
    require("オリジナルユニット" not in listing or "$boxes" in listing, "Artist categories were hard-coded away")
    require("kZvvnMDZHXU" in detail, "Requested YouTube video missing")
    require("2年間の進修課程を修了" in detail, "Two-year Shanghai study wording missing")
    for url in (
        "https://x.com/MUSICIAN_MEGUMI?s=20",
        "https://www.threads.com/@megmilk323?hl=ja",
        "https://www.facebook.com/da.ting.megumi/about",
        "https://www.instagram.com/megmilk323/",
    ):
        require(url in detail, f"SNS URL missing: {url}")
    require("$tbl_id = 62" in home, "Homepage Megumi slot replacement missing")
    require("/images/megumi-portrait-card.jpg?v=20260728b" in listing, "Artist image cache key missing")
    require("/images/megumi-portrait-card.jpg?v=20260728b" in home, "Homepage artist image cache key missing")
    require(
        sha256(WORKS / "app/webroot/images/megumi-portrait-card.jpg")
        == sha256(ARTIST / "app/webroot/images/artists/megumi-omachi/megumi-portrait-card.jpg"),
        "Artist listing image differs from approved portrait",
    )


def validate_works() -> None:
    template = (WORKS / "app/View/catalog/cl01_2/default/index.html").read_text(encoding="utf-8")
    css = (WORKS / "app/webroot/css/works_showcase.css").read_text(encoding="utf-8")
    require("style.css?v=20260728b" in template, "Works CSS cache key missing")
    require("hero-corporate-show-clean.webp?v=20260728b" in template, "Works showcase image cache key missing")
    require("-card.jpg?v=20260728b" in template, "Works gallery card cache key missing")
    require("-large.jpg?v=20260728b" in template, "Works gallery large-image cache key missing")
    require("grid-template-columns: repeat(4" in css, "Four-column Works gallery missing")
    for key in (
        "concert-opera-scene",
        "concert-operatic-heroines",
        "concert-orchestra-amber",
        "concert-soprano-stage",
    ):
        require(f"'image' => '{key}'" in template, f"Opera image missing: {key}")
    require("グループ全体" in template, "Taiko alt text does not preserve full group")
    taiko = WORKS / "app/webroot/images/works/gallery/traditional-taiko-card.jpg"
    with Image.open(taiko) as image:
        require(image.size == (960, 720), f"Taiko card is not 4:3: {image.size}")
        require(not image.getexif(), "Taiko EXIF remains")
    for stem, size in (
        ("hero-corporate-show-clean", (1920, 1080)),
        ("international-reception-clean", (1440, 900)),
        ("hotel-live-clean", (1440, 900)),
    ):
        for extension in ("jpg", "webp"):
            path = WORKS / f"app/webroot/images/works/{stem}.{extension}"
            with Image.open(path) as image:
                require(image.size == size, f"Edited Works image has wrong size: {path.name} {image.size}")
                require(not image.getexif(), f"Edited Works image retains EXIF: {path.name}")


def validate_seo_security() -> None:
    sitemap = (SEO / "app/webroot/sitemap.xml").read_text(encoding="utf-8")
    require("/achievements.html" in sitemap, "Achievements missing from sitemap")
    require("/artist/view/62" in sitemap, "Megumi page missing from sitemap")
    require("/company/index/" not in sitemap, "Redirected company archives remain in sitemap")
    require("2026-07-28" in sitemap, "Sitemap lastmod not updated")
    routes = (SEO / "app/Config/routes.php").read_text(encoding="utf-8")
    for category_id in (21, 20, 19, 18, 17, 16, 15, 14, 6, 5, 7, 13, 12):
        require(f"/company/index/{category_id}" in routes, f"Old archive redirect missing: {category_id}")
    htaccess = (SEO / "app/webroot/.htaccess").read_text(encoding="utf-8")
    for rule in (
        "Options -Indexes",
        'X-Content-Type-Options "nosniff"',
        'X-Frame-Options "SAMEORIGIN"',
        "Require all denied",
        "REQUEST_METHOD} ^TRACE$",
        "SampleKit|securimage|admin_sp",
    ):
        require(rule in htaccess, f"Security rule missing: {rule}")
    require("株式会社MUSICIAN" not in "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            COMPANY,
            ACHIEVEMENTS,
            ARTIST / "app/View/catalog/cl02_4/default/index.html",
            ARTIST / "app/View/catalog/cl02_4/default/view.html",
            WORKS / "app/View/catalog/cl01_2/default/index.html",
        )
    ), "Prohibited company name remains")


def validate_manifest_and_targets() -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    import deploy_full_production as deploy

    targets, summary = deploy.read_local_targets()
    require(not summary["manifest_mismatches"], f"Manifest mismatch: {summary['manifest_mismatches']}")
    for path in (
        "app/View/catalog/cl01_2/default/index.html",
        "app/View/catalog/cl01_3/default/index.html",
        "app/View/catalog/cl02_4/default/index.html",
        "app/View/catalog/cl02_4/default/view.html",
        "app/webroot/achievements.html",
        "app/webroot/css/style.css",
        "app/webroot/css/works_showcase.css",
        "app/webroot/css/artist_megumi.css",
        "app/webroot/images/company_photo_megumi.jpg",
        "app/webroot/images/company_photo_miyazaki_illustration.jpg",
        "app/webroot/images/megumi-portrait-card.jpg",
        "app/webroot/images/works/gallery/traditional-taiko-card.jpg",
    ):
        require(path in targets, f"Deployment target missing: {path}")


def main() -> None:
    validate_shared_headers()
    validate_about()
    validate_achievements()
    validate_artist()
    validate_works()
    validate_seo_security()
    validate_manifest_and_targets()
    print("Recovered release validation passed: headers, About, Achievements 2006-2026, Artist, Works, SEO, security and deployment targets.")


if __name__ == "__main__":
    main()
