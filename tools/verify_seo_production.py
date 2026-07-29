#!/usr/bin/env python3
"""Read-only production verification for the MUSICIAN SEO deployment."""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET


BASE = "https://www.musician.co.jp"
ERRORS: list[str] = []
CHECKS: list[str] = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE
OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=SSL_CONTEXT),
    NoRedirect(),
)


def fetch(path: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(
        BASE + path,
        headers={"User-Agent": "MUSICIAN-SEO-PostDeploy-Check/1.0"},
    )
    try:
        response = OPENER.open(request, timeout=25)
        return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, {key.lower(): value for key, value in exc.headers.items()}, exc.read()


def check(condition: bool, message: str) -> None:
    if condition:
        CHECKS.append(message)
    else:
        ERRORS.append(message)


def normalize_location(location: str) -> str:
    if location.startswith(BASE):
        return location[len(BASE) :] or "/"
    return location


def verify_html(path: str, canonical: str) -> str:
    status, _headers, payload = fetch(path)
    html = payload.decode("utf-8", errors="replace")
    check(status == 200, f"{path}: expected 200, got {status}")
    check("<?php" not in html, f"{path}: raw PHP leaked")
    check(html.count("<h1") == 1, f"{path}: expected one H1")
    check('rel="canonical"' in html, f"{path}: canonical tag missing")
    check(f'href="{BASE}{canonical}"' in html, f"{path}: canonical URL mismatch")
    check('property="og:title"' in html, f"{path}: OGP missing")
    check('name="twitter:card"' in html, f"{path}: Twitter card missing")
    match = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    check(match is not None, f"{path}: JSON-LD missing")
    if match is not None:
        try:
            structured = json.loads(match.group(1))
            graph = structured.get("@graph", [])
            types = [node.get("@type") for node in graph if isinstance(node, dict)]
            check("Organization" in types, f"{path}: Organization schema missing")
            check("WebSite" in types, f"{path}: WebSite schema missing")
        except json.JSONDecodeError as exc:
            ERRORS.append(f"{path}: invalid JSON-LD: {exc}")
    return html


def verify_redirect(path: str, destination: str) -> None:
    status, headers, _payload = fetch(path)
    location = headers.get("location", "")
    check(status == 301, f"{path}: expected 301, got {status}")
    check(
        normalize_location(location) == destination,
        f"{path}: expected Location {destination}, got {location or '(missing)'}",
    )


def main() -> int:
    pages = {
        "/": "/",
        "/business.html": "/business.html",
        "/works.html": "/works.html",
        "/artist.html": "/artist.html",
        "/company.html": "/company.html",
        "/achievements.html": "/achievements.html",
        "/contact.html": "/contact.html",
        "/artist/view/62": "/artist/view/62",
        "/artist-asakusa-taikoban.html": "/artist-asakusa-taikoban.html",
        "/works/index/4": "/works/index/4",
    }
    rendered = {path: verify_html(path, canonical) for path, canonical in pages.items()}
    company = rendered["/company.html"]
    achievements = rendered["/achievements.html"]
    artist = rendered["/artist.html"]
    megumi = rendered["/artist/view/62"]
    taikoban = rendered["/artist-asakusa-taikoban.html"]
    check(
        achievements.count('class="achievement-category-group__item"') == 85,
        "achievements: 85 recent achievements",
    )
    archive_occurrences = [
        int(value)
        for value in re.findall(
            r'achievement-category-group__item--archive" data-occurrences="(\d+)"',
            achievements,
        )
    ]
    check(sum(archive_occurrences) == 2672, "achievements: 2,672 recovered archive occurrences")
    check(len(archive_occurrences) < 2672, "achievements: recurring archive entries are collapsed")
    check("ランチタイムコンサート（年" in achievements, "achievements: lunchtime concert series is summarized")
    check(
        re.search(r'<details[^>]+id="achievements-2018"[\s\S]*?(?:19|20)\d{2}年\d{1,2}月\d{1,2}日', achievements) is None,
        "achievements: recovered event dates are hidden",
    )
    check(
        len(re.findall(r'<details[^>]+id="achievements-(?:20(?:0[6-9]|1\d|2[0-6]))"[^>]*\bopen\b', achievements)) == 21,
        "achievements: all 21 years are open by default",
    )
    check(
        "アーティスト協会 MUSICIAN事業部として継続している実績を含みます。" not in company,
        "company: removed association sentence is absent",
    )
    megumi_company_position = company.find("代表取締役 大町めぐみ")
    miyazaki_company_position = company.find("プロデューサー</span> 宮﨑 隆")
    check(
        0 <= megumi_company_position < miyazaki_company_position,
        "company: Megumi Omachi appears before Takashi Miyazaki",
    )
    check("私の音楽の原点は、小学生の頃にあります。" in company, "company: Miyazaki origin story")
    check("舞台監督として全体を見渡し" in company, "company: Miyazaki production leadership")
    check("約8,000曲分になりました。" in company, "company: Miyazaki arrangement archive count")
    check("その場にふさわしい音楽芸術をつくりましょう。" in company, "company: Miyazaki closing invitation")
    check("/artist/view/62" in artist and "大町 めぐみ" in artist, "artist: Megumi listing")
    check("/artist-asakusa-taikoban.html" in artist and "浅草たいこばん" in artist, "artist: Asakusa Taikoban listing")
    check("Japanese Taiko Drumming from the Heart of Asakusa" in taikoban, "Asakusa Taikoban: English profile")
    check("youtube-nocookie.com/embed/Vp875mBKNOU" in taikoban, "Asakusa Taikoban: YouTube embed")
    check("images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg" in taikoban, "Asakusa Taikoban: group image")
    check(
        ("上海音楽学院" in megumi or "上海音楽院" in megumi) and "2年間" in megumi,
        "Megumi profile: Shanghai study details",
    )
    for social in (
        "x.com/MUSICIAN_MEGUMI",
        "threads.com/@megmilk323",
        "facebook.com/da.ting.megumi",
        "instagram.com/megmilk323",
    ):
        check(social in megumi, f"Megumi profile: {social}")

    status, headers, _payload = fetch("/")
    check(status == 200, "home: security header response")
    for header in (
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "permissions-policy",
    ):
        check(bool(headers.get(header)), f"home: {header} security header")
    check(not headers.get("x-powered-by"), "home: X-Powered-By is hidden")

    redirects = {
        "/index.html": "/",
        "/works/index/22": "/works.html",
        "/works/index/22/page:1": "/works.html",
        "/company/index/21": "/achievements.html",
        "/company/index/20": "/achievements.html#achievements-2017",
        "/company.html?view=achievements": "/achievements.html",
        "/works/index/4/page:1": "/works/index/4",
        "/works/index/25/page:1": "/works/index/25",
    }
    for category_id in (5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19, 20):
        redirects[f"/company/index/{category_id}/page:1"] = f"/company/index/{category_id}"
    for path, destination in redirects.items():
        verify_redirect(path, destination)

    status, _headers, payload = fetch("/robots.txt")
    robots = payload.decode("utf-8", errors="replace")
    check(status == 200, f"robots.txt: expected 200, got {status}")
    check("Disallow: /\n" not in robots, "robots.txt: production is not globally blocked")
    check("Disallow: /media/" not in robots, "robots.txt: public media is crawlable")
    check(f"Sitemap: {BASE}/sitemap.xml" in robots, "robots.txt: sitemap declaration")

    status, _headers, payload = fetch("/sitemap.xml")
    check(status == 200, f"sitemap.xml: expected 200, got {status}")
    try:
        root = ET.fromstring(payload)
        namespace = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }
        locations = [node.text or "" for node in root.findall("sm:url/sm:loc", namespace)]
        image_locations = [node.text or "" for node in root.findall("sm:url/image:image/image:loc", namespace)]
        check(len(locations) == 37, f"sitemap.xml: 37 URLs, found {len(locations)}")
        check(len(image_locations) == 50, f"sitemap.xml: 50 images, found {len(image_locations)}")
        check(f"{BASE}/achievements.html" in locations, "sitemap.xml: independent achievements URL")
        check(f"{BASE}/artist-asakusa-taikoban.html" in locations, "sitemap.xml: Asakusa Taikoban URL")
        check(
            f"{BASE}/images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg" in image_locations,
            "sitemap.xml: Asakusa Taikoban group image",
        )
        check(
            f"{BASE}/images/artists/asakusa-taikoban/asakusa-taikoban-performance.jpg" in image_locations,
            "sitemap.xml: Asakusa Taikoban performance image",
        )
        check(len(locations) == len(set(locations)), "sitemap.xml: URLs are unique")
    except ET.ParseError as exc:
        ERRORS.append(f"sitemap.xml: invalid XML: {exc}")

    status, _headers, payload = fetch("/nonexistent-codex-seo-check.html")
    missing = payload.decode("utf-8", errors="replace")
    check(status == 404, f"unknown .html: expected 404, got {status}")
    check("ページが見つかりません" in missing, "unknown .html: friendly 404 body")
    check('name="robots" content="noindex, follow"' in missing, "unknown .html: noindex")

    for sample_path in (
        "/.git/config",
        "/.env",
        "/composer.json",
        "/app/Config/database.php",
        "/wp-login.php",
        "/xmlrpc.php",
        "/_bk_20221124/",
        "/SampleKit/",
        "/securimage/example_form.php",
        "/ez_js/eq/",
        "/ez_js/pdf/web/",
    ):
        status, _headers, _payload = fetch(sample_path)
        expected = (403, 404)
        check(status in expected, f"{sample_path}: expected blocked status {expected}, got {status}")

    result = {
        "passed": len(CHECKS),
        "failed": len(ERRORS),
        "errors": ERRORS,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for error in ERRORS:
            annotation = (
                error.replace("%", "%25")
                .replace("\r", "%0D")
                .replace("\n", "%0A")
            )
            print(f"::error title=Production verification failed::{annotation}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    raise SystemExit(main())
