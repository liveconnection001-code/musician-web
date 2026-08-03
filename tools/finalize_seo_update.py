from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from build_home_preview import build as build_home_preview


ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "new_site" / "seo_deployment"
PREVIEW = ROOT / "temporary_preview_site" / "public"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def replace_once_idempotent(text: str, old: str, new: str, label: str) -> str:
    """Apply a one-time transformation, or accept an already-finalized file."""
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        return text.replace(old, new, 1)
    if old_count == 0 and new_count == 1:
        return text
    raise RuntimeError(
        f"{label}: expected one source or one finalized match, "
        f"found source={old_count}, finalized={new_count}"
    )


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def ensure_guide_header_nav(text: str) -> str:
    """Keep Guide between Achievements and the mobile-only Contact item."""
    legacy_footer_label = '<span class="en">Guide / ' + 'FAQ</span>'
    text = text.replace(legacy_footer_label, '<span class="en">Guide</span>')
    header, marker, remainder = text.partition("</header>")
    if not marker:
        return text
    if re.search(
        r'<li(?: class="navi-on")?><a href="/?guide\.html"><span class="en">Guide</span></a></li>',
        header,
    ):
        return text
    pattern = re.compile(
        r'(?P<indent>^[ \t]*)'
        r'(?P<achievements><li(?: class="navi-on")?><a href="(?P<root>/?)achievements\.html">'
        r'<span class="en">Achievements</span></a></li>)',
        re.MULTILINE,
    )
    header, count = pattern.subn(
        lambda match: (
            f'{match.group("indent")}{match.group("achievements")}\n'
            f'{match.group("indent")}<li><a href="{match.group("root")}guide.html">'
            '<span class="en">Guide</span></a></li>'
        ),
        header,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"Guide header nav: expected one insertion point, found {count}")
    return header + marker + remainder


def finalize_deployment() -> None:
    home_path = DEPLOYMENT / "app" / "View" / "Homes" / "index.html"
    home = home_path.read_text(encoding="utf-8")
    home = replace_once_idempotent(
        home,
        '<img class="object-fit-img cover" loading="lazy" decoding="async" src="images/mv/mv_img01.jpg" alt="企業イベントを彩るプロ演奏家の生演奏" fetchpriority="high" decoding="async">',
        '<img class="object-fit-img cover" src="images/mv/mv_img01.jpg" alt="企業イベントを彩るプロ演奏家の生演奏" fetchpriority="high" decoding="async">',
        "home priority image",
    )
    home = ensure_guide_header_nav(home)
    write(home_path, home)

    company_path = DEPLOYMENT / "app" / "View" / "catalog" / "cl01_3" / "default" / "index.html"
    company = company_path.read_text(encoding="utf-8")
    company = replace_once_idempotent(
        company,
        "  'seoPageType' => 'CollectionPage',",
        "  'seoPageType' => $seoIsRoot ? 'AboutPage' : 'CollectionPage',",
        "company schema page type",
    )
    company = ensure_guide_header_nav(company)
    write(company_path, company)


def finalize_preview() -> None:
    company_path = PREVIEW / "company.html"
    company = company_path.read_text(encoding="utf-8")
    old_meta = (
        '<title>出張演奏、演奏依頼はMUSICIAN｜実績紹介</title>\n'
        '<meta name="description" content="MUSICIANでは、プロ演奏家の出張演奏サービス、パーティ・披露宴の演出企画・出張演奏、公共・福祉施設や事業所、商業施設へのイベント企画演奏、アーティストのマネジメント、育成、企画などをいたしております。">\n'
        '<meta name="keywords" content="出張演奏,MUSICIAN,生演奏,クラシック,社歌制作,オーケストラ,ジャズ,ピアノ,バイオリン">'
    )
    new_meta = (
        '<title>MUSICIANについて・演奏実績｜公開前確認</title>\n'
        '<meta name="description" content="出張演奏・イベント音楽制作のMUSICIANについて、2019年から2026年までの主な企業イベント、式典、ホテル、商業施設、学校公演などの実績をご確認いただけます。">\n'
        '<meta name="robots" content="noindex, nofollow">'
    )
    company = replace_once_idempotent(company, old_meta, new_meta, "preview metadata")
    company = replace_once_idempotent(
        company,
        '<h1 class="osu3"><a href="https://www.musician.co.jp/index.html"><img src="images/head_logo_1.png" alt="プロ演奏家の出張演奏サービスはMUSICIAN。" class="img-fluid"></a></h1>',
        '<div class="site-logo osu3"><a href="https://www.musician.co.jp/"><img src="images/head_logo_1.png" alt="出張演奏・イベント音楽制作のMUSICIAN" class="img-fluid" width="478" height="138"></a></div>',
        "preview header logo",
    )
    company = replace_once_idempotent(
        company,
        '<h2 data-aos="fade-up"><span>About us</span>私たちについて</h2>',
        '<h1 data-aos="fade-up"><span>About us</span>私たちについて</h1>',
        "preview H1",
    )
    company = company.replace('target="_blank"', 'target="_blank" rel="noopener noreferrer"')
    company = company.replace('2022 MUSICIAN.CO.JP', '2022–2026 MUSICIAN.CO.JP')
    company = ensure_guide_header_nav(company)
    write(company_path, company)

    css_path = PREVIEW / "css" / "style.css"
    css = css_path.read_text(encoding="utf-8")
    css = css.replace("h1 {float: left;}", ".site-logo {float: left;}")
    css = css.replace("h1 img{", ".site-logo img{")
    css = css.replace(".cb-header h1 img{", ".cb-header .site-logo img{")
    css = css.replace("#midashi_h2 h2", "#midashi_h2 h1")
    write(css_path, css)
    for filename in ("bootstrap.js", "title.js"):
        source = DEPLOYMENT / "app" / "webroot" / "js" / filename
        destination = PREVIEW / "js" / filename
        write(destination, source.read_text(encoding="utf-8"))


def refresh_manifest() -> None:
    manifest_path = DEPLOYMENT / "seo_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = []
    for path in sorted(p for p in DEPLOYMENT.rglob("*") if p.is_file() and p != manifest_path and p.name != "CLAUDE_REVIEW.md"):
        payload = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(DEPLOYMENT).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest["file_count"] = len(files)
    manifest["files"] = files
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    finalize_deployment()
    finalize_preview()
    build_home_preview()
    refresh_manifest()
    print("Finalized SEO deployment and private preview")


if __name__ == "__main__":
    main()
