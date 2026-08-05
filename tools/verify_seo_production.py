#!/usr/bin/env python3
"""Read-only production verification for the MUSICIAN SEO deployment."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


BASE = "https://www.musician.co.jp"
GA4_MEASUREMENT_ID = "G-74ETNWY2T9"
RETIRED_GA4_MEASUREMENT_ID = "G-N0RQ" + "FSVHCM"
ERRORS: list[str] = []
CHECKS: list[str] = []
FETCH_TIMEOUT_SECONDS = int(os.environ.get("MUSICIAN_VERIFY_FETCH_TIMEOUT_SECONDS", "20"))
TARGET_MAX_ATTEMPTS = min(3, max(1, int(os.environ.get("MUSICIAN_VERIFY_TARGET_MAX_ATTEMPTS", "3"))))
TARGET_RETRY_DELAY_SECONDS = int(os.environ.get("MUSICIAN_VERIFY_TARGET_RETRY_DELAY_SECONDS", "15"))
# Reserve 30 seconds inside the workflow's hard eight-minute timeout so that
# the verifier can always emit its rollback/manual-check decision itself.
VERIFY_BUDGET_SECONDS = int(os.environ.get("MUSICIAN_VERIFY_BUDGET_SECONDS", "450"))
CONTROL_PATH = os.environ.get("MUSICIAN_VERIFY_CONTROL_PATH", "/robots.txt")
RESULT_PATH = os.environ.get("MUSICIAN_VERIFY_RESULT_PATH", "production-verify-result.json")
STARTED_AT = time.monotonic()


@dataclass
class FetchResult:
    status: int
    headers: dict[str, str]
    payload: bytes
    curl_exit: int
    duration_ms: int

    def __iter__(self):
        yield self.status
        yield self.headers
        yield self.payload


class ManualCheckRequired(RuntimeError):
    """The runner cannot reach both a page and its unchanged control URL."""


class TargetUnavailable(RuntimeError):
    """Only the target URL failed after a reachable control URL and retries."""


class ContentVerificationFailure(RuntimeError):
    """A response proves a deployed page or required SEO resource is invalid."""


def _remaining_seconds() -> int:
    return int(VERIFY_BUDGET_SECONDS - (time.monotonic() - STARTED_AT))


def _is_transport_failure(result: FetchResult) -> bool:
    return result.status == 0


def _parse_headers(raw: bytes) -> dict[str, str]:
    blocks = re.split(r"\r?\n\r?\n", raw.decode("iso-8859-1", errors="replace"))
    for block in reversed(blocks):
        lines = block.splitlines()
        if lines and lines[0].startswith("HTTP/"):
            return {
                key.strip().lower(): value.strip()
                for line in lines[1:]
                if ":" in line
                for key, value in [line.split(":", 1)]
            }
    return {}


def _fetch_once(path: str, *, purpose: str, attempt: int) -> FetchResult:
    remaining = _remaining_seconds()
    if remaining <= 0:
        raise ManualCheckRequired(
            f"検証時間予算 {VERIFY_BUDGET_SECONDS} 秒を使い切りました。手動で9ページ200とSEO検証を実施してください。"
        )

    request_timeout = max(1, min(FETCH_TIMEOUT_SECONDS, remaining))
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="musician_verify_") as temp_dir:
        temp = Path(temp_dir)
        body_path = temp / "body"
        headers_path = temp / "headers"
        completed = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--insecure",
                "--max-time",
                str(request_timeout),
                "--connect-timeout",
                str(min(3, request_timeout)),
                "--output",
                str(body_path),
                "--dump-header",
                str(headers_path),
                "--write-out",
                "%{http_code}",
                "--header",
                "User-Agent: MUSICIAN-SEO-PostDeploy-Check/2.0",
                "--header",
                "Cache-Control: no-cache",
                "--header",
                "Pragma: no-cache",
                BASE + path,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        duration_ms = round((time.monotonic() - started) * 1000)
        status_text = completed.stdout.strip()
        status = int(status_text) if status_text.isdigit() else 0
        payload = body_path.read_bytes() if body_path.exists() else b""
        headers = _parse_headers(headers_path.read_bytes()) if headers_path.exists() else {}

    result = FetchResult(status, headers, payload, completed.returncode, duration_ms)
    print(
        "HTTP_PROBE "
        + json.dumps(
            {
                "path": path,
                "purpose": purpose,
                "attempt": attempt,
                "http_status": result.status,
                "curl_exit": result.curl_exit,
                "duration_ms": result.duration_ms,
            },
            ensure_ascii=False,
        )
    )
    return result


def establish_initial_control() -> None:
    """Probe an unchanged resource before checking any deployed page."""
    control = _fetch_once(CONTROL_PATH, purpose="initial-control", attempt=1)
    if not _is_transport_failure(control):
        return

    target = _fetch_once("/", purpose="initial-target-after-control-failure", attempt=1)
    control_retry = _fetch_once(CONTROL_PATH, purpose="initial-control-retry", attempt=2)
    if _is_transport_failure(target) and _is_transport_failure(control_retry):
        raise ManualCheckRequired(
            "対照URLと対象ページの両方が応答不能です。ロールバックせず、手動で9ページ200とSEO検証を実施してください。"
        )
    raise ManualCheckRequired(
        "対照URLの通信状態が不安定です。ロールバックせず、手動で9ページ200とSEO検証を実施してください。"
    )


def fetch(path: str) -> FetchResult:
    target = _fetch_once(path, purpose="target", attempt=1)
    if not _is_transport_failure(target):
        return target

    control_path = "/" if path == CONTROL_PATH else CONTROL_PATH
    control = _fetch_once(control_path, purpose="control-after-target-failure", attempt=1)
    if _is_transport_failure(control):
        raise ManualCheckRequired(
            f"{path} と対照URL {control_path} の両方が応答不能です。ロールバックせず、手動で9ページ200とSEO検証を実施してください。"
        )

    for attempt in range(2, TARGET_MAX_ATTEMPTS + 1):
        if TARGET_RETRY_DELAY_SECONDS:
            time.sleep(TARGET_RETRY_DELAY_SECONDS)
        target = _fetch_once(path, purpose="target-retry", attempt=attempt)
        if not _is_transport_failure(target):
            return target

    raise TargetUnavailable(
        f"{path} は対照URL取得可の状態で{TARGET_MAX_ATTEMPTS}回とも応答不能でした。内容起因の可能性としてロールバックします。"
    )


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
    if 400 <= status <= 599:
        raise ContentVerificationFailure(f"{path}: expected 200, got {status}")
    html = payload.decode("utf-8", errors="replace")
    check(status == 200, f"{path}: expected 200, got {status}")
    check("<?php" not in html, f"{path}: raw PHP leaked")
    check("\u6d3e\u9063" not in html, f"{path}: prohibited service wording remains")
    check(html.count("<h1") == 1, f"{path}: expected one H1")
    check('rel="canonical"' in html, f"{path}: canonical tag missing")
    check(f'href="{BASE}{canonical}"' in html, f"{path}: canonical URL mismatch")
    check('property="og:title"' in html, f"{path}: OGP missing")
    check('name="twitter:card"' in html, f"{path}: Twitter card missing")
    check(
        html.count(GA4_MEASUREMENT_ID) == 2,
        f"{path}: expected company-owned GA4 ID twice",
    )
    check(
        RETIRED_GA4_MEASUREMENT_ID not in html,
        f"{path}: retired GA4 ID remains",
    )
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
    if 400 <= status <= 599:
        raise ContentVerificationFailure(f"{path}: expected 301, got {status}")
    location = headers.get("location", "")
    check(status == 301, f"{path}: expected 301, got {status}")
    check(
        normalize_location(location) == destination,
        f"{path}: expected Location {destination}, got {location or '(missing)'}",
    )


def verify() -> bool:
    establish_initial_control()
    pages = {
        "/": "/",
        "/business.html": "/business.html",
        "/equipment.html": "/equipment.html",
        "/works.html": "/works.html",
        "/artist.html": "/artist.html",
        "/company.html": "/company.html",
        "/achievements.html": "/achievements.html",
        "/contact.html": "/contact.html",
        "/guide.html": "/guide.html",
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
    equipment = rendered["/equipment.html"]
    check("機材費に利益を上乗せしません。" in equipment, "equipment: value proposition")
    check(
        "自社案件でご利用いただく機材です（機材単体のレンタルは行っていません）。" in equipment,
        "equipment: in-house project disclaimer",
    )
    check("スピーカー 24台" in equipment, "equipment: speaker count")
    check("<strong>48ch</strong><span>最大同時入力数</span>" in equipment, "equipment: mixer capacity label")
    check("業務用4Kカメラ 4台、2Kカメラ 8台" in equipment, "equipment: camera counts")
    check("音響だけ、映像だけでも。" not in equipment, "equipment: no standalone audio/video offer")
    check("音楽芸術をつくるための、" in equipment, "equipment: artistic-production positioning")
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
    check("約8,000曲になりました。" in company, "company: Miyazaki arrangement archive count")
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

    for admin_path in ("/admin", "/admin/", "/admin/index.php", "/admin/webroot/"):
        status, _headers, _payload = fetch(admin_path)
        check(status == 403, f"{admin_path}: expected 403, got {status}")

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
    if 400 <= status <= 599:
        raise ContentVerificationFailure(f"robots.txt: expected 200, got {status}")
    robots = payload.decode("utf-8", errors="replace")
    check(status == 200, f"robots.txt: expected 200, got {status}")
    check("Disallow: /\n" not in robots, "robots.txt: production is not globally blocked")
    check("Disallow: /media/" not in robots, "robots.txt: public media is crawlable")
    check(f"Sitemap: {BASE}/sitemap.xml" in robots, "robots.txt: sitemap declaration")

    status, _headers, payload = fetch("/sitemap.xml")
    if 400 <= status <= 599:
        raise ContentVerificationFailure(f"sitemap.xml: expected 200, got {status}")
    check(status == 200, f"sitemap.xml: expected 200, got {status}")
    try:
        root = ET.fromstring(payload)
        namespace = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }
        locations = [node.text or "" for node in root.findall("sm:url/sm:loc", namespace)]
        image_locations = [node.text or "" for node in root.findall("sm:url/image:image/image:loc", namespace)]
        check(len(locations) == 39, f"sitemap.xml: 39 URLs, found {len(locations)}")
        check(len(image_locations) == 54, f"sitemap.xml: 54 images, found {len(image_locations)}")
        for gallery_image in (
            "traditional-taiko-ceremony-large.jpg",
            "traditional-shamisen-tatami-large.jpg",
            "jazz-female-big-band-stage-large.jpg",
            "traditional-mariachi-festive-large.jpg",
        ):
            check(
                f"{BASE}/images/works/gallery/{gallery_image}" in image_locations,
                f"sitemap.xml: missing Works gallery image {gallery_image}",
            )
        check(f"{BASE}/achievements.html" in locations, "sitemap.xml: independent achievements URL")
        check(f"{BASE}/equipment.html" in locations, "sitemap.xml: Equipment URL")
        check(f"{BASE}/artist-asakusa-taikoban.html" in locations, "sitemap.xml: Asakusa Taikoban URL")
        check(f"{BASE}/guide.html" in locations, "sitemap.xml: Guide / FAQ URL")
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

    return not ERRORS


def finish(decision: str) -> int:
    result = {
        "passed": len(CHECKS),
        "failed": len(ERRORS),
        "errors": ERRORS,
        "decision": decision,
        "elapsed_ms": round((time.monotonic() - STARTED_AT) * 1000),
        "control_url": BASE + CONTROL_PATH,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    Path(RESULT_PATH).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for error in ERRORS:
            annotation = (
                error.replace("%", "%25")
                .replace("\r", "%0D")
                .replace("\n", "%0A")
            )
            print(f"::error title=Production verification failed::{annotation}")
    return {"verified": 0, "rollback": 1, "manual_check": 2}[decision]


def main() -> int:
    try:
        return finish("verified" if verify() else "rollback")
    except ManualCheckRequired as exc:
        ERRORS.append(str(exc))
        print("MANUAL_CONFIRMATION_REQUIRED: 9ページのHTTP 200と公開SEO検証をローカルから実施してください。")
        return finish("manual_check")
    except TargetUnavailable as exc:
        ERRORS.append(str(exc))
        return finish("rollback")
    except ContentVerificationFailure as exc:
        ERRORS.append(str(exc))
        return finish("rollback")
    except Exception as exc:
        ERRORS.append(f"検証実行環境の内部エラー: {exc}")
        print("MANUAL_CONFIRMATION_REQUIRED: 検証器の異常終了です。ロールバックせず、手動で9ページ200とSEO検証を実施してください。")
        return finish("manual_check")


if __name__ == "__main__":
    raise SystemExit(main())
