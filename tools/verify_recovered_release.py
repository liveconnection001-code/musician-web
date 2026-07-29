#!/usr/bin/env python3
"""Strict validation for the approved 2026-07-28 MUSICIAN release."""

from __future__ import annotations

import hashlib
import html
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
        require("style.css?v=20260730a" in text, f"{label}: CSS cache key missing")
    css = STYLE.read_text(encoding="utf-8")
    require("approved shared page heading" in css, "Approved heading CSS missing")
    require(re.search(r"#midashi_h2\s*\{[^}]*height:\s*40px", css, re.S), "Navy band is not 40px")
    require("@media screen and (max-width: 767px)" in css, "Mobile heading rules missing")


def validate_about() -> None:
    text = COMPANY.read_text(encoding="utf-8")
    megumi = text.index("代表取締役</span> 大町めぐみ")
    miyazaki = text.index("プロデューサー</span> 宮﨑 隆")
    require(megumi < miyazaki, "About us profile order is wrong")
    require("company_photo_megumi.jpg?v=20260730a" in text, "Megumi About image cache key missing")
    require("company_photo_miyazaki_illustration.jpg?v=20260730a" in text, "Miyazaki illustration cache key missing")
    require("recent-achievements" not in text and 'id="achievements"' not in text, "Achievements remain in About us")
    require("Career" not in text, "Removed Career section remains")
    require("私の音楽の原点は、小学生の頃にあります。" in text, "Miyazaki origin story is missing")
    require("舞台監督として全体を見渡し" in text, "Miyazaki production leadership is missing")
    require("約8,000曲分になりました。" in text, "Miyazaki arrangement archive count is missing")
    require("その場にふさわしい音楽芸術をつくりましょう。" in text, "Miyazaki closing invitation is missing")
    require(text.count("<span>About us</span>私たちについて") == 1, "About us title is duplicated")
    preview_company = ROOT / "temporary_preview_site/public/company.html"
    if preview_company.is_file():
        preview = preview_company.read_text(encoding="utf-8")
        require(preview.count("<span>About us</span>私たちについて") == 1, "Local About us preview has a duplicate page title")
        require("Career" not in preview, "Local About us preview contains the removed Career section")

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
    require(len(re.findall(r'<details class="achievement-year(?: achievement-year--archive)?"[^>]*\sopen(?:\s|>)', text)) == 21, "All 21 years must be open by default")
    require("ISEKI Global Awards</span><span class=\"achievement-list__detail\">ソプラノ歌唱の出演手配" in text, "Achievement title/detail are not kept inline")
    require("recent_achievements.css?v=20260730a" in text, "Achievements CSS missing")
    require("seoCanonicalPath' => '/achievements.html'" in text, "Achievements canonical missing")
    require("2006年から2026年" in text, "Achievements description does not cover full archive")

    recovered = {int(item["year"]): item for item in json.loads(RECOVERED.read_text(encoding="utf-8"))}
    require(set(recovered) == set(range(2006, 2019)), "Recovered years incomplete")
    archive_total = 0
    archive_rows = 0
    for year, item in recovered.items():
        match = re.search(
            rf'<details class="achievement-year achievement-year--archive" id="achievements-{year}" open>(.*?)</details>',
            text,
            flags=re.S,
        )
        require(match is not None, f"Recovered {year} section missing")
        rendered_entries = [
            (
                html.unescape(re.sub(r"<[^>]+>", " ", title)).strip(),
                int(count),
            )
            for count, title in re.findall(
                r'<li class="achievement-category-group__item achievement-category-group__item--archive" '
                r'data-occurrences="(\d+)">.*?<span class="achievement-list__title">(.*?)</span>',
                match.group(1),
                flags=re.S,
            )
        ]
        source_titles = []
        for raw_entry in re.findall(r"<p>(.*?)</p>", item["html"], flags=re.S):
            title = html.unescape(re.sub(r"<[^>]+>", " ", raw_entry))
            title = " ".join(title.replace("\u3000", " ").split())
            title = re.sub(
                r"^\s*(?:19|20)\d{2}年(?:\s*\d{1,2}月(?:\s*\d{1,2}日)?)?"
                r"(?:\s*[～〜-]\s*(?:\d{1,2}月)?\s*\d{1,2}日)?\s*",
                "",
                title,
            ).strip()
            if title:
                source_titles.append(title)
        require(sum(count for _title, count in rendered_entries) == len(source_titles), f"Recovered {year} occurrence count changed")
        require(len(rendered_entries) <= len(source_titles), f"Recovered {year} aggregation increased rows")
        require(
            not any(re.match(r"^(?:19|20)\d{2}年\d{1,2}月", title) for title, _count in rendered_entries),
            f"Recovered {year} still displays event dates",
        )
        require('class="achievement-list__category"' in match.group(1), f"Recovered {year} is not grouped")
        archive_total += sum(count for _title, count in rendered_entries)
        archive_rows += len(rendered_entries)
    require(archive_total == 2672, f"Recovered archive item count changed: {archive_total}")
    require(
        text.count('class="achievement-category-group__item achievement-category-group__item--archive"') == archive_rows,
        "Archive rendered row count changed",
    )
    require(archive_rows < archive_total, "Recurring archive entries were not collapsed")
    require("ランチタイムコンサート（年" in text, "Lunchtime concert series was not summarized")

    css = ACHIEVEMENTS_CSS.read_text(encoding="utf-8")
    require("grid-template-columns: minmax(0, 1fr) 150px" in css, "Category width is not 150px")
    require("position: sticky" in css and "align-self: stretch" in css, "Sticky Category is incomplete")
    require(".achievements-category a::before" in css, "CSS year arrow missing")
    require("grid-template-columns: repeat(3, 1fr)" in css, "Mobile Category layout missing")
    require(".achievement-list__line" in css and "display: flex" in css, "Inline achievement layout missing")


def validate_artist() -> None:
    listing = (ARTIST / "app/View/catalog/cl02_4/default/index.html").read_text(encoding="utf-8")
    detail = (ARTIST / "app/View/catalog/cl02_4/default/view.html").read_text(encoding="utf-8")
    home = (ARTIST / "app/View/Homes/index.html").read_text(encoding="utf-8")
    taikoban = (ARTIST / "app/webroot/artist-asakusa-taikoban.html").read_text(encoding="utf-8")
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
    require("/images/megumi-portrait-card.jpg?v=20260730a" in listing, "Artist image cache key missing")
    require("/images/megumi-portrait-card.jpg?v=20260730a" in home, "Homepage artist image cache key missing")
    require(
        sha256(WORKS / "app/webroot/images/megumi-portrait-card.jpg")
        == sha256(ARTIST / "app/webroot/images/artists/megumi-omachi/megumi-portrait-card.jpg"),
        "Artist listing image differs from approved portrait",
    )
    require("/artist-asakusa-taikoban.html" in listing, "Asakusa Taikoban listing link missing")
    require("浅草たいこばん" in listing and "アサクサ タイコバン" in listing, "Asakusa Taikoban listing text missing")
    require("浅草たいこばん" in taikoban and "Asakusa Taikoban" in taikoban, "Asakusa Taikoban bilingual name missing")
    require("Japanese Taiko Drumming from the Heart of Asakusa" in taikoban, "English profile heading missing")
    require("corporate events" in taikoban and "inbound tourism programs" in taikoban, "English booking copy missing")
    require("youtube-nocookie.com/embed/Vp875mBKNOU" in taikoban, "Asakusa Taikoban YouTube embed missing")
    require("youtu.be/Vp875mBKNOU" in taikoban, "Asakusa Taikoban YouTube link missing")
    require("<span>Artist</span>アーティスト" in taikoban, "Asakusa Taikoban shared Artist header missing")
    require("株式会社MUSICIAN" not in taikoban, "Prohibited company name remains on Asakusa Taikoban page")
    taikoban_images = ARTIST / "app/webroot/images/artists/asakusa-taikoban"
    for name, expected in (
        ("asakusa-taikoban-card.jpg", (800, 600)),
        ("asakusa-taikoban-group.jpg", (1200, 900)),
        ("asakusa-taikoban-performance.jpg", (1200, 1600)),
    ):
        with Image.open(taikoban_images / name) as image:
            require(image.size == expected, f"Asakusa Taikoban image size mismatch: {name} {image.size}")
            require(not image.getexif(), f"Asakusa Taikoban EXIF remains: {name}")


def validate_works() -> None:
    template = (WORKS / "app/View/catalog/cl01_2/default/index.html").read_text(encoding="utf-8")
    css = (WORKS / "app/webroot/css/works_showcase.css").read_text(encoding="utf-8")
    require("style.css?v=20260730a" in template, "Works CSS cache key missing")
    require("hero-corporate-show-clean.webp?v=20260730a" in template, "Works showcase image cache key missing")
    require("-card.jpg?v=20260730a" in template, "Works gallery card cache key missing")
    require("-large.jpg?v=20260730a" in template, "Works gallery large-image cache key missing")
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
    require("/artist-asakusa-taikoban.html" in sitemap, "Asakusa Taikoban page missing from sitemap")
    require("images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg" in sitemap, "Asakusa Taikoban image missing from sitemap")
    require("/company/index/" not in sitemap, "Redirected company archives remain in sitemap")
    require("2026-07-30" in sitemap, "Sitemap lastmod not updated")
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
        "app/webroot/css/artist_taikoban.css",
        "app/webroot/artist-asakusa-taikoban.html",
        "app/webroot/images/artists/asakusa-taikoban/asakusa-taikoban-card.jpg",
        "app/webroot/images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg",
        "app/webroot/images/artists/asakusa-taikoban/asakusa-taikoban-performance.jpg",
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
