from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "new_site" / "seo_deployment"
PREVIEW = ROOT / "temporary_preview_site"
ERRORS: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def text(relative_path: str) -> str:
    return (DEPLOYMENT / relative_path).read_text(encoding="utf-8")


def validate_manifest() -> None:
    manifest = json.loads(text("seo_manifest.json"))
    check(manifest.get("production_uploaded") is False, "manifest must say production_uploaded=false")
    check(manifest.get("file_count") == 32, "deployment must contain 32 staged files")
    expected = {entry["path"] for entry in manifest.get("files", [])}
    check("app/View/Elements/seo_meta.html" in expected, "SEO metadata element missing from manifest")
    check("app/webroot/sitemap.xml" in expected, "sitemap missing from manifest")
    check("app/webroot/js/bootstrap.js" in expected, "guarded Bootstrap script missing from manifest")
    check("app/webroot/js/title.js" in expected, "guarded title animation script missing from manifest")
    check("app/webroot/guide.html" in expected, "Guide / FAQ page missing from manifest")
    check("app/webroot/css/mus_guide.css" in expected, "Guide / FAQ CSS missing from manifest")
    check("app/webroot/css/mus_reasons.css" in expected, "Top reasons CSS missing from manifest")
    check("app/webroot/css/mus_record.css" in expected, "Top achievements strip CSS missing from manifest")


def validate_templates() -> None:
    indexed_templates = [
        "app/View/Homes/index.html",
        "app/webroot/business.html",
        "app/webroot/equipment.html",
        "app/webroot/contact.html",
        "app/webroot/guide.html",
        "app/View/catalog/cl01_2/default/index.html",
        "app/View/catalog/cl01_3/default/index.html",
        "app/View/catalog/cl02_4/default/index.html",
        "app/View/catalog/cl02_4/default/view.html",
    ]
    for relative_path in indexed_templates:
        page = text(relative_path)
        check("element('seo_meta'" in page, f"{relative_path}: shared SEO element is not called")
        check('<h1 class="osu3">' not in page, f"{relative_path}: logo is still the page H1")
        expected_h1_templates = 1
        check(page.count("<h1") == expected_h1_templates, f"{relative_path}: unexpected H1 template count")
    check('class="site-logo osu3"' in page, f"{relative_path}: semantic logo wrapper missing")

    public_templates = indexed_templates + ["app/View/Contact/msg.html", "app/View/Contact/thanks.html"]
    for relative_path in public_templates:
        page = text(relative_path)
        check("株式会社MUSICIAN" not in page, f"{relative_path}: obsolete company name remains")
        check("instagram.com/musician_inc" not in page, f"{relative_path}: obsolete Instagram URL remains")
        check("instagram.com/musician_office_/" in page, f"{relative_path}: current Instagram URL missing")
        check("2022 MUSICIAN.CO.JP" not in page, f"{relative_path}: copyright year is stale")
        check("2022–2026 MUSICIAN.CO.JP" in page, f"{relative_path}: copyright range missing")
        headings = [int(level) for level in re.findall(r"<h([1-6])\b", page, re.I)]
        check(
            all(current <= previous + 1 for previous, current in zip(headings, headings[1:])),
            f"{relative_path}: heading hierarchy skips a level: {headings}",
        )

    element = text("app/View/Elements/seo_meta.html")
    for token in (
        'rel="canonical"',
        'property="og:title"',
        'name="twitter:card"',
        'application/ld+json',
        "'@type' => 'Organization'",
        "'@type' => 'WebSite'",
        "'@type' => 'BreadcrumbList'",
    ):
        check(token in element, f"SEO element missing: {token}")

    home = text("app/View/Homes/index.html")
    check('class="pd_yohaku_r home-works"' in home, "home: curated Works section missing")
    check("requestAction(array('controller'=>'works'" not in home, "home: legacy Works CMS request returned")
    check('style.css?v=20260802f' in home, "home: shared stylesheet cache key missing")
    check('mus_reasons.css?v=20260802c' in home, "home: reasons stylesheet missing")
    check(home.count('class="mus-reasons__item"') == 3, "home: expected three reasons")
    for token in (
        "演奏、編曲、舞台美術、照明、音響まで。",
        "音楽家が率いる制作チームが、企画から本番までを一つの手でつくりあげます。",
        "JRA賞授賞式、企業表彰式、国際レセプション、ホテル・商業施設、コンサートホール ——",
        "2006年から積み重ねた実績は2,000件を超えます。",
        "MUSICIANは、演奏の現場を知る音楽家が中心となって運営する、音楽芸術の制作会社です。",
        "舞台のすべてを、一つの窓口で",
        "ご予算を、成果に変える設計をします",
    ):
        check(token in home, f"home: approved Phase 3 copy missing: {token}")
    check('mus_record.css?v=20260803a' in home, "home: achievements strip stylesheet missing")
    check('href="achievements.html"' in home, "home: achievements strip link missing")
    check("配信" not in home, "home: streaming remains in promotional copy")

    guide = text("app/webroot/guide.html")
    check(guide.count("'@type' => 'Question'") == 8, "guide: FAQPage schema must contain eight questions")
    check(guide.count('class="mus-guide__faq-item"') == 8, "guide: page must display eight questions")
    check(guide.count("'@type' => 'FAQPage'") == 1, "guide: FAQPage schema must be output once")
    check("ご予算に合わせて編成をご提案します" in guide, "guide: budget-planning heading missing")
    check("まずはご相談ください" in guide and 'href="contact.html"' in guide, "guide: contact CTA missing")
    check(re.search(r"(?:¥|￥|\d[\d,]*(?:円|万円))", guide) is None, "guide: prohibited price amount found")
    site_css = text("app/webroot/css/style.css")
    for token in (
        ".home-works__genres",
        ".top_works .box .text",
        ".top_artist .box .text",
        "text-align: center;",
        "width: 38%;",
        "height: min(420px, calc(100% - 48px));",
        "#top01 .photo{height: 170px;}",
    ):
        check(token in site_css, f"home: compact About/Works CSS missing: {token}")
    home_works = re.search(
        r'<div class="top_works clearfix".*?</div>\s*'
        r'<p class="home-works__genres">.*?</p>\s*'
        r'<p class="tar_sptac">',
        home,
        re.DOTALL,
    )
    check(home_works is not None, "home: Works genre block missing")
    if home_works:
        works_block = home_works.group(0)
        expected_images = (
            "recent-anniversary-big-band",
            "recent-orchestra-soprano-gala",
            "japanese-hospitality-clean",
            "recent-roaming-jazz-band",
            "recent-fusion-stage",
            "recent-corporate-jazz-band",
        )
        expected_labels = (
            "情熱が踊る、ラテンの響き",
            "格式を彩る、オーケストラ",
            "凛と華やぐ、和の響き",
            "笑顔を運ぶ、デキシージャズ",
            "悠久を奏でる、中国の音色",
            "心躍る、華やかなポップス",
        )
        for key in expected_images:
            check(key in works_block, f"home: Works genre photo missing: {key}")
        labels = tuple(re.findall(r'<div class="text">([^<]+)</div>', works_block))
        check(labels == expected_labels, f"home: Works genre labels/order changed: {labels}")
        check(
            "フラメンコ、ケルト音楽、ブルーグラス、タンゴ、フレンチジャズ、ミュゼット、"
            "カンツォーネ、カントリー、ボサノバ、マリアッチ、サンバなど、"
            "さまざまなジャンルの実施例もご覧いただけます。" in works_block,
            "home: additional genre guidance missing",
        )
        check(
            home.index('class="top_works clearfix"') < home.index('class="home-works__genres"'),
            "home: additional genre guidance must follow the six genre cards",
        )
        check("recent-orchestra-banquet" not in works_block, "home: duplicate orchestra photo returned")
        check("live-streaming-clean" not in works_block, "home: streaming photo returned")
    first_image = re.search(r'<img[^>]+fetchpriority="high"[^>]*>', home)
    check(first_image is not None, "home LCP image missing")
    if first_image:
        tag = first_image.group(0)
        check('fetchpriority="high"' in tag, "home LCP image must have high fetch priority")
        check('loading="lazy"' not in tag, "home LCP image must not be lazy-loaded")
        check(tag.count('decoding="async"') == 1, "home LCP image has duplicate decoding attributes")

    for artist_id, artist_name in (
        ("63", "Black Venus"),
        ("56", "Mary Quartet"),
        ("55", "「和花」～waka～"),
    ):
        check(
            f"{artist_id} => '{artist_name}'" in home,
            f"home: concise Artist display name missing for ID {artist_id}",
        )

    artist_index = text("app/View/catalog/cl02_4/default/index.html")
    check(
        'artist_megumi.css?v=20260730b' in artist_index,
        "artist: alignment stylesheet cache key missing",
    )
    for artist_id, artist_name in (
        ("63", "Black Venus"),
        ("56", "Mary Quartet"),
        ("55", "「和花」～waka～"),
    ):
        check(
            f"{artist_id} => '{artist_name}'" in artist_index,
            f"artist: concise display name missing for ID {artist_id}",
        )

    business = text("app/webroot/business.html")
    for token in (
        "MUSICIANは、出演者をご紹介して終わりの会社ではありません。",
        "舞台美術、照明、音響、当日の進行までを一体で統括する、音楽芸術の総合制作会社です。",
        "オペラをはじめとする舞台作品を、美術や衣装まで含めてつくり上げてきた経験が土台にあります。",
        "個人のお客様のご依頼も承ります。",
    ):
        check(token in business, f"business: approved Phase 3 copy missing: {token}")
    check("ディラー" not in business and "ディーラー" in business, "business: dealer spelling is not corrected")
    check("equipment.html" in business, "business: Equipment page link missing")

    equipment = text("app/webroot/equipment.html")
    for token in (
        "音と映像の仕上がりを、",
        "自社機材と自社技術で、",
        "機材費に利益を上乗せしません。",
        "自社案件でご利用いただく機材です（機材単体のレンタルは行っていません）。",
        "スピーカー 24台",
        "<strong>48ch</strong><span>最大同時入力数</span>",
        "業務用4Kカメラ 4台、2Kカメラ 8台",
        "ステージボックス 4台、イヤーモニター 8台",
        "配信用パソコン 4台、スイッチャー 3台",
    ):
        check(token in equipment, f"equipment: required content missing: {token}")
    check("音響だけ、映像だけでも。" not in equipment, "equipment: standalone audio/video offer remains")
    check("音楽芸術をつくるための、" in equipment, "equipment: artistic-production positioning missing")
    check("音楽・演出・機材を相談する" in equipment, "equipment: integrated consultation label missing")
    for prohibited in ("低価格", "安い", "格安", "お得", "安さ", "原価"):
        check(prohibited not in equipment, f"equipment: prohibited value wording remains: {prohibited}")
    check(".equipment-hero" in site_css, "equipment: page styles missing")

    company = text("app/View/catalog/cl01_3/default/index.html")
    check("$seoIsRoot ? 'AboutPage' : 'CollectionPage'" in company, "company page schema type not specialized")
    check("/achievements.html" in company, "independent achievements URL missing")
    check("achievement-category-group__item" not in company, "About page must not contain achievement listings")
    check("アーティスト協会 MUSICIAN事業部として継続している実績を含みます。" not in company, "removed association sentence returned")

    achievements = text("app/webroot/achievements.html")
    check(
        achievements.count('class="achievement-category-group__item">') == 85,
        "expected 85 recent achievement items",
    )
    archive_occurrences = [
        int(value)
        for value in re.findall(
            r'achievement-category-group__item--archive" data-occurrences="(\d+)"',
            achievements,
        )
    ]
    check(sum(archive_occurrences) == 2672, "expected 2672 historical achievement occurrences")
    check(
        len(archive_occurrences) < 2672,
        "historical recurring achievements were not collapsed",
    )
    check("ランチタイムコンサート（年" in achievements, "recurring lunchtime concerts were not summarized")

    for relative_path in ("app/View/Contact/msg.html", "app/View/Contact/thanks.html"):
        page = text(relative_path)
        check('name="robots" content="noindex, nofollow"' in page, f"{relative_path}: noindex missing")


def validate_javascript() -> None:
    bootstrap = text("app/webroot/js/bootstrap.js")
    title = text("app/webroot/js/title.js")
    check("throw new Error('Bootstrap tooltips require Tether" not in bootstrap, "Bootstrap still throws when unused Tether is absent")
    check(title.count("if (!scrollElemToWatch_1) return;") == 7, "title animation guards must cover all seven remaining optional targets")
    check("setTimeout(banner1" not in title, "primary page heading must not use delayed reveal animation")
    check("banner.style.visibility = 'visible';" in title, "primary page heading must be visible from first paint")

def validate_sitemap_and_robots() -> None:
    sitemap_path = DEPLOYMENT / "app" / "webroot" / "sitemap.xml"
    root = ET.parse(sitemap_path).getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text or "" for node in root.findall("sm:url/sm:loc", namespace)]
    check(len(urls) == 39, f"sitemap must contain 39 page URLs, found {len(urls)}")
    check("https://www.musician.co.jp/equipment.html" in urls, "Equipment URL missing from sitemap")
    check("https://www.musician.co.jp/achievements.html" in urls, "independent achievements URL missing from sitemap")
    check("https://www.musician.co.jp/artist-asakusa-taikoban.html" in urls, "Asakusa Taikoban URL missing from sitemap")
    check("https://www.musician.co.jp/guide.html" in urls, "Guide / FAQ URL missing from sitemap")
    check(len(urls) == len(set(urls)), "sitemap contains duplicate URLs")
    check(all(url.startswith("https://www.musician.co.jp/") for url in urls), "sitemap contains a non-canonical host")
    check(all("?" not in url and "#" not in url and "/page:1" not in url for url in urls), "sitemap contains non-canonical variants")
    for duplicate in (
        "https://www.musician.co.jp/index.html",
        "https://www.musician.co.jp/works/index/22",
        "https://www.musician.co.jp/company/index/21",
    ):
        check(duplicate not in urls, f"duplicate URL remains in sitemap: {duplicate}")

    robots = text("app/View/Homes/robots.html")
    check("Disallow: /media/" not in robots, "public media is still blocked from image search")
    check("Sitemap: https://www.musician.co.jp/sitemap.xml" in robots, "robots sitemap declaration missing")
    for blocked in ("/admin_sp/", "/_dl/", "/SampleKit/", "/ez_js/pdf/web/"):
        check(f"Disallow: {blocked}" in robots, f"robots rule missing: {blocked}")


def validate_routing() -> None:
    root_htaccess = text(".htaccess")
    for destination in ("works/index/22", "company/index/21", "works/index/$1", "company/index/$1"):
        check(destination in root_htaccess, f"canonical redirect missing: {destination}")
    check(
        "company/index/(5|6|7|12|13|14|15|16|17|18|19|20)/page:1" in root_htaccess,
        "company category page:1 redirects are missing or incomplete",
    )
    webroot_htaccess = text("app/webroot/.htaccess")
    check(r"\tRewrite" not in webroot_htaccess and r"\t#" not in webroot_htaccess, "webroot .htaccess contains literal backslash-t directives")
    for sample in ("SampleKit", "securimage", "ez_js/eq", "ez_js/pdf/web"):
        check(sample in webroot_htaccess, f"sample 404 rule missing: {sample}")
    routes = text("app/Config/routes.php")
    controller = text("app/Controller/HomesController.php")
    check("/:slug.html" in routes and "not_found" in routes, "unknown .html route missing")
    check("$this->response->statusCode(404)" in controller, "true 404 status is missing")
    check("$this->render('/Errors/error400')" in controller, "friendly 404 render is missing")
    error_page = text("app/View/Errors/error400.html")
    check('name="robots" content="noindex, follow"' in error_page, "404 page noindex missing")


def validate_service_wording() -> None:
    prohibited_words = ("\u6d3e\u9063", "低価格", "安い", "格安")
    checked_suffixes = {".html", ".php", ".xml", ".json", ".txt"}
    for path in DEPLOYMENT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in checked_suffixes:
            continue
        page = path.read_text(encoding="utf-8", errors="replace")
        for prohibited in prohibited_words:
            check(
                prohibited not in page,
                f"{path.relative_to(DEPLOYMENT).as_posix()}: prohibited service wording remains: {prohibited}",
            )

    brand_paths = (
        "app/View/Homes/index.html",
        "app/webroot/business.html",
        "app/webroot/contact.html",
        "app/webroot/equipment.html",
        "app/View/catalog/cl01_2/default/index.html",
    )
    for relative_path in brand_paths:
        page = text(relative_path)
        check("手配" not in page, f"{relative_path}: '手配' remains in brand copy")

    for relative_path in ("app/View/Homes/index.html", "app/webroot/business.html"):
        page = text(relative_path)
        for subject in ("舞台美術", "照明", "衣装"):
            check(
                re.search(rf"{subject}.{{0,50}}(?:保有|完備)|(?:保有|完備).{{0,50}}{subject}", page) is None,
                f"{relative_path}: unsupported ownership wording is attached to {subject}",
            )


def validate_preview() -> None:
    # The browser preview is intentionally local-only and excluded from Git.
    # CI validates the deployable package; local runs additionally validate the
    # private noindex preview when it is present.
    if not PREVIEW.is_dir():
        print("Local-only browser preview is absent; preview checks skipped.")
        return
    check((PREVIEW / "app" / "seo" / "page.tsx").is_file(), "SEO preview route is missing")
    check((PREVIEW / "app" / "seo" / "seo.css").is_file(), "SEO preview stylesheet is missing")
    preview_company = (PREVIEW / "public" / "company.html").read_text(encoding="utf-8")
    check('name="robots" content="noindex, nofollow"' in preview_company, "private company preview must remain noindex")
    check(preview_company.count("<h1") == 1, "private company preview must have one H1")
    preview_home_path = PREVIEW / "public" / "home.html"
    check(preview_home_path.is_file(), "full homepage preview is missing")
    if preview_home_path.is_file():
        preview_home = preview_home_path.read_text(encoding="utf-8")
        check("<?php" not in preview_home and "?>" not in preview_home, "homepage preview contains PHP")
        check('name="robots" content="noindex, nofollow"' in preview_home, "homepage preview must remain noindex")
        check(preview_home.count('class="box" role="listitem"') >= 6, "homepage preview must show six Works cards")


def main() -> None:
    validate_manifest()
    validate_templates()
    validate_javascript()
    validate_sitemap_and_robots()
    validate_routing()
    validate_service_wording()
    validate_preview()
    if ERRORS:
        print("SEO validation failed:")
        for error in ERRORS:
            print(f"- {error}")
        sys.exit(1)
    print("SEO validation passed: 32 files, 39 canonical URLs, 85 recent achievements and 2672 historical occurrences")


if __name__ == "__main__":
    main()
