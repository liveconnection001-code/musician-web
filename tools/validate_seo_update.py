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
    check(manifest.get("file_count") == 23, "deployment must contain 23 staged files")
    expected = {entry["path"] for entry in manifest.get("files", [])}
    check("app/View/Elements/seo_meta.html" in expected, "SEO metadata element missing from manifest")
    check("app/webroot/sitemap.xml" in expected, "sitemap missing from manifest")
    check("app/webroot/js/bootstrap.js" in expected, "guarded Bootstrap script missing from manifest")
    check("app/webroot/js/title.js" in expected, "guarded title animation script missing from manifest")


def validate_templates() -> None:
    indexed_templates = [
        "app/View/Homes/index.html",
        "app/webroot/business.html",
        "app/webroot/contact.html",
        "app/View/catalog/cl01_2/default/index.html",
        "app/View/catalog/cl01_3/default/index.html",
        "app/View/catalog/cl02_4/default/index.html",
        "app/View/catalog/cl02_4/default/view.html",
    ]
    for relative_path in indexed_templates:
        page = text(relative_path)
        check("element('seo_meta'" in page, f"{relative_path}: shared SEO element is not called")
        check('<h1 class="osu3">' not in page, f"{relative_path}: logo is still the page H1")
        expected_h1_templates = 1 if relative_path == "app/View/catalog/cl01_3/default/index.html" else 1
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
    case_ids = (
        "work-corporate-event",
        "work-international-reception",
        "work-japanese-culture",
        "work-hotel-party",
        "work-large-venue",
        "work-live-streaming",
    )
    check('class="pd_yohaku_r home-works"' in home, "home: curated Works section missing")
    check("requestAction(array('controller'=>'works'" not in home, "home: legacy Works CMS request returned")
    check(len(re.findall(r'images/works/[^"\']+-clean\.jpg', home)) == 6, "home: expected six clean Works JPEGs")
    for case_id in case_ids:
        check(f'href="works.html#{case_id}"' in home, f"home: link to {case_id} missing")
    first_image = re.search(r'<img[^>]+mv_img01\.jpg[^>]*>', home)
    check(first_image is not None, "home LCP image missing")
    if first_image:
        tag = first_image.group(0)
        check('fetchpriority="high"' in tag, "home LCP image must have high fetch priority")
        check('loading="lazy"' not in tag, "home LCP image must not be lazy-loaded")
        check(tag.count('decoding="async"') == 1, "home LCP image has duplicate decoding attributes")

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
    check(
        achievements.count("achievement-category-group__item--archive") == 2672,
        "expected 2672 date-free historical achievement items",
    )

    for relative_path in ("app/View/Contact/msg.html", "app/View/Contact/thanks.html"):
        page = text(relative_path)
        check('name="robots" content="noindex, nofollow"' in page, f"{relative_path}: noindex missing")


def validate_javascript() -> None:
    bootstrap = text("app/webroot/js/bootstrap.js")
    title = text("app/webroot/js/title.js")
    check("throw new Error('Bootstrap tooltips require Tether" not in bootstrap, "Bootstrap still throws when unused Tether is absent")
    check(title.count("if (!scrollElemToWatch_1) return;") == 8, "title animation guards must cover all eight optional targets")

def validate_sitemap_and_robots() -> None:
    sitemap_path = DEPLOYMENT / "app" / "webroot" / "sitemap.xml"
    root = ET.parse(sitemap_path).getroot()
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text or "" for node in root.findall("sm:url/sm:loc", namespace)]
    check(len(urls) == 36, f"sitemap must contain 36 page URLs, found {len(urls)}")
    check("https://www.musician.co.jp/achievements.html" in urls, "independent achievements URL missing from sitemap")
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


def validate_preview() -> None:
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
        check(len(re.findall(r'images/works/[^"\']+-clean\.jpg', preview_home)) == 6, "homepage preview must show six clean Works images")


def main() -> None:
    validate_manifest()
    validate_templates()
    validate_javascript()
    validate_sitemap_and_robots()
    validate_routing()
    validate_preview()
    if ERRORS:
        print("SEO validation failed:")
        for error in ERRORS:
            print(f"- {error}")
        sys.exit(1)
    print("SEO validation passed: 23 files, 36 canonical URLs, 85 recent and 2672 historical achievements")


if __name__ == "__main__":
    main()
