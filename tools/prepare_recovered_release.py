#!/usr/bin/env python3
"""Prepare the reviewed whole-site release without rolling back unrelated work."""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parents[1]
SEO = ROOT / "new_site" / "seo_deployment"
ARTIST = ROOT / "new_site" / "artist_deployment"
WORKS = ROOT / "new_site" / "works_deployment"
RECOVERED = ROOT / "work" / "recovered_achievements_2006_2018.json"
STYLE = SEO / "app" / "webroot" / "css" / "style.css"
ACHIEVEMENTS_CSS = ROOT / "new_site" / "deployment" / "app" / "webroot" / "css" / "recent_achievements.css"
SEO_ACHIEVEMENTS_CSS = SEO / "app" / "webroot" / "css" / "recent_achievements.css"
RECENT_ACHIEVEMENTS_SOURCE = ROOT / "new_site" / "deployment" / "app" / "View" / "catalog" / "cl01_3" / "default" / "index.html"
COMPANY = SEO / "app" / "View" / "catalog" / "cl01_3" / "default" / "index.html"
ACHIEVEMENTS = SEO / "app" / "webroot" / "achievements.html"
BUSINESS = SEO / "app" / "webroot" / "business.html"
ROUTES = SEO / "app" / "Config" / "routes.php"
SITEMAP = SEO / "app" / "webroot" / "sitemap.xml"
MANIFEST = SEO / "seo_manifest.json"
ASSET_VERSION = "20260730a"
STYLE_VERSION = "20260730a"


ARCHIVE_DATE_RE = re.compile(
    r"^\s*(?:19|20)\d{2}年(?:\s*\d{1,2}月(?:\s*\d{1,2}日)?)?"
    r"(?:\s*[～〜-]\s*(?:\d{1,2}月)?\s*\d{1,2}日)?\s*"
)
ARCHIVE_CATEGORY_RULES = (
    ("クルーズ", ("クルーズ", "ぱしふぃっくびいなす", "ぱしふぃっく びいなす", "飛鳥", "にっぽん丸", "船上", "船内", "船長主催")),
    ("CM・広告", ("CM", "ＣＭ", "広告", "キャンペーン", "プロモーション", "PRイベント", "キャスティング")),
    ("テレビ・メディア", ("テレビ", "TV", "ＴＶ", "番組", "ラジオ", "放送", "NHK", "ＮＨＫ", "取材", "雑誌")),
    ("録音・楽曲制作", ("レコーディング", "録音", "音源", "編曲", "作曲", "譜面", "アルバム", "CD制作", "ＣＤ制作", "ミキシング", "マスタリング")),
    ("式典・表彰", ("授賞", "受賞", "表彰", "式典", "贈呈式", "賀詞", "祝賀", "竣工", "落成", "開業", "開所", "開会式", "閉会式", "セレモニー", "入学式", "卒業式", "結婚式", "披露宴", "叙勲", "記念式", "周年記念")),
    ("国際イベント", ("国際", "大使館", "外国人", "海外", "ワールド", "サウジアラビア", "シンガポール", "ドバイ", "中国政府", "日中", "日韓")),
    ("スポーツイベント", ("競馬", "ファンファーレ", "ゴルフ", "サッカー", "野球", "マラソン", "スポーツ", "モーターサイクル", "オリンピック", "パラリンピック")),
    ("音響・運営", ("音響", "PA", "ＰＡ", "舞台監督", "オペレーション", "会場運営", "制作運営", "進行管理")),
    ("ホテル・施設", ("ホテル", "ハーヴェスト", "ハーベスト", "リゾート", "宴会場", "レストラン", "病院", "ロビー", "BAR", "ＢＡＲ", "Bar", "ラウンジ")),
    ("百貨店・商業施設", ("百貨店", "髙島屋", "高島屋", "マルイ", "丸井", "イオン", "モール", "商業施設", "デパート", "東武", "伊勢丹", "三越", "そごう", "ルミネ", "ららぽーと", "銀座スクエア")),
    ("定期公演", ("定期公演", "定例公演", "定期演奏会", "月例コンサート", "ランチタイムコンサート")),
    ("コンサート", ("コンサート", "リサイタル", "ライブ", "LIVE", "ＬＩＶＥ", "演奏会", "音楽会", "公演", "ステージ", "ショー")),
    ("企業イベント", ("株式会社", "会社", "企業", "懇親会", "パーティ", "Party", "Ｐａｒｔｙ", "新年会", "忘年会", "総会", "会議", "セミナー", "展示会", "イベント", "フェア", "代理店会", "販売店")),
    ("地域・文化イベント", ("神社", "寺", "祭", "文化", "自治体", "市民", "学校", "学園", "新春", "お正月", "獅子舞")),
    ("出張演奏", ("出張演奏", "演奏サービス", "演奏", "出演", "奏者", "アーティスト")),
)


SHARED_HEADING_CSS = r"""

/* 2026-07-28: approved shared page heading for Business, Artist, About us,
   artist profiles and Achievements. The thin navy divider and white title
   field intentionally match the approved About us / Works relationship. */
#midashi_h2 {
  background: #041e42;
  display: block !important;
  height: 40px;
  margin-bottom: 170px;
  margin-top: 45px;
  padding: 0;
  position: relative;
}
#midashi_h2 .container-fluid {
  padding-left: 0;
  padding-right: 0;
  position: static;
}
#midashi_h2 .yohaku {
  background: #eee;
  color: #041e42;
  display: block;
  left: 0;
  margin: 0;
  padding: 28px max(5vw, calc((100vw - 1540px) / 2)) 22px;
  position: absolute;
  right: 0;
  top: 40px;
}
#midashi_h2 h1 {
  display: block;
  font-family: "Shippori Mincho", serif;
  font-size: clamp(18px, 1.6vw, 25px);
  font-weight: 600;
  letter-spacing: .025em;
  line-height: 1.45;
  margin: 0;
  padding: 0;
  text-align: left;
}
#midashi_h2 h1 span {
  display: block;
  font-family: "Urbanist", sans-serif;
  font-size: clamp(54px, 6vw, 86px);
  font-weight: 500;
  letter-spacing: .1em;
  line-height: 1.12;
  margin-bottom: 12px;
}
#midashi_h2 [data-aos] {
  opacity: 1 !important;
  transform: none !important;
  transition: none !important;
}
#midashi_h2 .pankuzu { display: none; }
main > .content_pd:first-child,
#banner1 + main > section:first-child > .content_pd:first-child { padding-top: 18px; }
.company-profile p { line-height: 2; margin-bottom: 1em; }
.company-profile + .company-profile {
  border-top: 1px solid rgba(4, 30, 66, .18);
  padding-top: 50px;
}
@media print, screen and (min-width: 768px) { #midashi_h2 { margin-top: 60px; } }
@media print, screen and (min-width: 1200px) { #midashi_h2 { margin-top: 80px; } }
@media screen and (max-width: 767px) {
  #midashi_h2 { margin-bottom: 132px; }
  #midashi_h2 .yohaku { padding: 24px 24px 18px; }
  #midashi_h2 h1 { font-size: 17px; }
  #midashi_h2 h1 span {
    font-size: clamp(34px, 10.8vw, 52px);
    letter-spacing: .06em;
    margin-bottom: 8px;
  }
  main > .content_pd:first-child,
  #banner1 + main > section:first-child > .content_pd:first-child { padding-top: 16px; }
}
"""


ACHIEVEMENTS_LAYOUT_CSS = r"""

/* 2026-07-28: independent Achievements page and narrow sticky year category. */
.achievements-content { padding-top: 18px; }
.achievements-layout {
  display: grid;
  gap: clamp(30px, 4vw, 60px);
  grid-template-columns: minmax(0, 1fr) 150px;
}
.achievements-main { min-width: 0; }
.achievements-sidebar { align-self: stretch; min-width: 0; }
.achievements-category {
  background: #f7f7f7;
  border-top: 3px solid #041e42;
  max-height: calc(100vh - 130px);
  overflow-y: auto;
  padding: 15px 11px 13px;
  position: sticky;
  scrollbar-color: rgba(4, 30, 66, .35) transparent;
  scrollbar-width: thin;
  top: 112px;
}
.achievements-category::-webkit-scrollbar { width: 3px; }
.achievements-category::-webkit-scrollbar-track { background: transparent; }
.achievements-category::-webkit-scrollbar-thumb {
  background: rgba(4, 30, 66, .2);
  border-radius: 999px;
}
.achievements-category h2 {
  color: #041e42;
  font-family: "Urbanist", sans-serif;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: .06em;
  margin: 0 3px 10px;
}
.achievements-category ul { list-style: none; margin: 0; padding: 0; }
.achievements-category li { border-top: 1px solid rgba(4, 30, 66, .12); }
.achievements-category a {
  color: #041e42;
  display: block;
  font-family: "Urbanist", sans-serif;
  font-size: 14px;
  letter-spacing: .04em;
  padding: 7px 2px 7px 16px;
  position: relative;
}
.achievements-category a::before {
  border-right: 1px solid currentColor;
  border-top: 1px solid currentColor;
  content: "";
  height: 6px;
  left: 2px;
  position: absolute;
  top: 14px;
  transform: rotate(45deg);
  width: 6px;
}
.achievements-category a:hover,
.achievements-category a:focus-visible { color: #b34c18; text-decoration: none; }
.achievement-year { scroll-margin-top: 130px; }
.achievement-year__body--archive .ezm_htmlarea p {
  border-top: 1px dotted rgba(4, 30, 66, .22);
  font-size: 14px;
  line-height: 1.75;
  margin: 0;
  padding: 10px 0;
}
.achievement-year__body--archive .ezm_htmlarea p:first-child { border-top: 0; }
@media (max-width: 767.98px) {
  .achievements-layout { display: flex; flex-direction: column; gap: 28px; }
  .achievements-sidebar { order: -1; width: 100%; }
  .achievements-category { max-height: none; position: static; }
  .achievements-category ul { display: grid; grid-template-columns: repeat(3, 1fr); }
  .achievements-category li { border-right: 1px solid rgba(4, 30, 66, .12); }
}
"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def cache_bust(text: str) -> str:
    return re.sub(
        r'href="css/style\.css(?:\?v=[^"]+)?"',
        f'href="css/style.css?v={STYLE_VERSION}"',
        text,
    )


def cache_bust_images(text: str) -> str:
    """Force browsers to refresh the reviewed public image assets."""
    text = re.sub(
        r'((?:https://www\.musician\.co\.jp/|/)?images/works/[A-Za-z0-9_./-]+\.(?:jpe?g|webp))(?:\?v=[^"\'<>\s]+)?',
        rf'\1?v={ASSET_VERSION}',
        text,
        flags=re.I,
    )
    text = re.sub(
        r'(-(?:card|large)\.jpg)(?:\?v=[^"\'<>\s]+)?(?=["\'])',
        rf'\1?v={ASSET_VERSION}',
        text,
        flags=re.I,
    )
    text = re.sub(
        r'(/?images/(?:megumi-portrait-card|company_photo_megumi|company_photo_miyazaki_illustration)\.jpg)(?:\?v=[^"\'<>\s]+)?',
        rf'\1?v={ASSET_VERSION}',
        text,
        flags=re.I,
    )
    return text


def prepare_style() -> None:
    text = STYLE.read_text(encoding="utf-8")
    marker = "/* 2026-07-28: approved shared page heading"
    start = text.find(marker)
    if start >= 0:
        text = text[:start].rstrip() + SHARED_HEADING_CSS
    else:
        text = text.rstrip() + SHARED_HEADING_CSS
    write_text(STYLE, text)


def prepare_company() -> None:
    text = COMPANY.read_text(encoding="utf-8")
    text = cache_bust_images(cache_bust(text))
    text = text.replace(' rel="noopener noreferrer" rel="noopener noreferrer"', ' rel="noopener noreferrer"')
    text = text.replace('\t<link href="css/sidemenu2.css" rel="stylesheet"><!--サイドメニュー-->\n', '')
    text = text.replace('<link href="css/recent_achievements.css" rel="stylesheet"><!--近年の実績-->\n', '')
    text = text.replace(
        "MUSICIANについて・演奏実績｜出張演奏・演奏家派遣",
        "MUSICIANについて｜株式会社東京アーティスト協会",
    )
    text = text.replace(
        "出張演奏・演奏家派遣のMUSICIANについて、サービス方針と2010年から2026年までの主な企業イベント、式典、ホテル、商業施設、学校公演などの実績をご紹介します。",
        "株式会社東京アーティスト協会が運営するMUSICIANの会社情報と、音楽・芸術制作に携わる大町めぐみ、宮﨑隆のプロフィールをご紹介します。",
    )
    text = text.replace(
        '<h2 class="midashi1 mb30_md50 tal_sptac"><span class="en">About us</span>私たちについて</h2>\n',
        "",
        1,
    )
    text = text.replace(
        '<img src="images/company_photo01.jpg" alt="宮﨑 隆"',
        '<img src="images/company_photo_miyazaki_illustration.jpg" alt="宮﨑 隆の似顔絵"',
        1,
    )
    marker = '\n<section>\n\t<div id="cate_head"></div>'
    start = text.find(marker)
    if start >= 0:
        end = text.find("</main>", start)
        if end < 0:
            raise RuntimeError("About us main closing tag not found")
        text = text[:start] + "\n\n</main>" + text[end + len("</main>"):]
    if "id=\"achievements\"" in text or "recent-achievements" in text:
        raise RuntimeError("Achievements content remains in About us")
    write_text(COMPANY, text)


def sync_artist() -> None:
    for relative in (
        Path("app/View/Homes/index.html"),
        Path("app/View/catalog/cl02_4/default/index.html"),
        Path("app/View/catalog/cl02_4/default/view.html"),
    ):
        source = ARTIST / relative
        text = cache_bust_images(cache_bust(source.read_text(encoding="utf-8")))
        write_text(ARTIST / relative, text)
        write_text(SEO / relative, text)

    # These three approved root-level assets are referenced by CMS templates.
    shared_images = WORKS / "app" / "webroot" / "images"
    shared_images.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        ARTIST / "app/webroot/images/artists/megumi-omachi/megumi-portrait-card.jpg",
        shared_images / "megumi-portrait-card.jpg",
    )
    shutil.copyfile(
        ROOT / "work/release_upload/4_achievements/images/company_photo_megumi.jpg",
        shared_images / "company_photo_megumi.jpg",
    )
    shutil.copyfile(
        ROOT / "work/approved_assets/miyazaki_portrait_illustration.jpg",
        shared_images / "company_photo_miyazaki_illustration.jpg",
    )


def seo_block() -> str:
    return """<?php echo $this->element('seo_meta', array(
  'seoTitle' => '音楽制作・出張演奏の実績一覧｜MUSICIAN',
  'seoDescription' => '2006年から2026年までの音楽制作、企業イベント、式典、ホテル・商業施設、コンサート、配信・映像などの実績を年度別にご紹介します。',
  'seoCanonicalPath' => '/achievements.html',
  'seoPageType' => 'CollectionPage',
  'seoBreadcrumbItems' => array(
    array('name' => 'ホーム', 'item' => '/'),
    array('name' => '実績一覧', 'item' => '/achievements.html')
  )
)); ?>"""


def group_recent_achievements(recent: str) -> str:
    """Group each recent year by service category and keep entries compact."""
    item_pattern = re.compile(
        r'<li class="achievement-list__item">\s*'
        r'<span class="achievement-list__category">(.*?)</span>\s*'
        r'<div class="achievement-list__content">\s*'
        r'<p class="achievement-list__title">(.*?)</p>\s*'
        r'<p class="achievement-list__detail">(.*?)</p>\s*'
        r'</div>\s*</li>',
        flags=re.S,
    )

    def replace_list(match: re.Match[str]) -> str:
        grouped: dict[str, list[tuple[str, str]]] = {}
        for category, title, detail in item_pattern.findall(match.group(1)):
            grouped.setdefault(category.strip(), []).append((title.strip(), detail.strip()))
        if not grouped:
            return match.group(0)

        blocks = []
        for category, entries in grouped.items():
            lines = "\n".join(
                f'''              <li class="achievement-category-group__item">
                <p class="achievement-list__line"><span class="achievement-list__title">{title}</span><span class="achievement-list__detail">{detail}</span></p>
              </li>'''
                for title, detail in entries
            )
            blocks.append(f'''          <section class="achievement-category-group">
            <h3 class="achievement-list__category">{category}</h3>
            <ul class="achievement-category-group__list">
{lines}
            </ul>
          </section>''')
        return "\n".join(blocks)

    recent = re.sub(
        r'<ul class="achievement-list">\s*(.*?)\s*</ul>',
        replace_list,
        recent,
        flags=re.S,
    )
    return re.sub(
        r'(<details class="achievement-year" id="achievements-\d{4}")(?:\s+open)?>',
        r'\1 open>',
        recent,
    )


def archive_entry_text(raw_html: str) -> str:
    """Return an archive entry without its former publication date."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw_html))
    text = " ".join(text.replace("\u3000", " ").split())
    return ARCHIVE_DATE_RE.sub("", text).strip()


def archive_category(title: str) -> str:
    folded = title.casefold()
    for category, keywords in ARCHIVE_CATEGORY_RULES:
        if any(keyword.casefold() in folded for keyword in keywords):
            return category
    return "その他の実績"


def archive_group_key(title: str) -> str:
    """Return a conservative key for repeated legacy entries in one year."""
    normalized = re.sub(r"\s+", "", title).casefold()
    if normalized == "株ランチタイムコンサート":
        normalized = "ランチタイムコンサート"
    normalized = normalized.replace("ランチコンサート", "ランチタイムコンサート")
    return normalized


def collapse_archive_entries(entries: list[str]) -> list[tuple[str, int]]:
    """Collapse indistinguishable recurring work while preserving annual counts."""
    grouped: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for title in entries:
        key = archive_group_key(title)
        if key not in grouped:
            display = re.sub(r"^株(?=ランチタイムコンサート$)", "", title)
            display = display.replace("ランチコンサート", "ランチタイムコンサート")
            grouped[key] = {"title": display, "count": 0}
            order.append(key)
        grouped[key]["count"] = int(grouped[key]["count"]) + 1

    collapsed: list[tuple[str, int]] = []
    for key in order:
        item = grouped[key]
        title = str(item["title"])
        count = int(item["count"])
        collapsed.append((f"{title}（年{count}回）" if count > 1 else title, count))
    return collapsed


def group_archive_achievements(archive_html: str) -> str:
    """Group legacy entries like the 2019+ layout and remove event dates."""
    grouped: dict[str, list[str]] = {}
    for raw_entry in re.findall(r"<p>(.*?)</p>", archive_html, flags=re.S):
        title = archive_entry_text(raw_entry)
        if not title:
            continue
        grouped.setdefault(archive_category(title), []).append(title)

    blocks: list[str] = []
    for category, entries in grouped.items():
        entries = collapse_archive_entries(entries)
        lines = "\n".join(
            f'''              <li class="achievement-category-group__item achievement-category-group__item--archive" data-occurrences="{count}">
                <p class="achievement-list__line"><span class="achievement-list__title">{html.escape(title, quote=False)}</span></p>
              </li>'''
            for title, count in entries
        )
        blocks.append(f'''          <section class="achievement-category-group">
            <h3 class="achievement-list__category">{category}</h3>
            <ul class="achievement-category-group__list">
{lines}
            </ul>
          </section>''')
    return "\n".join(blocks)


def prepare_achievements() -> None:
    source = RECENT_ACHIEVEMENTS_SOURCE.read_text(encoding="utf-8")
    recent_start = source.find('<section class="recent-achievements"')
    recent_end = source.find("</section>", recent_start)
    if recent_start < 0 or recent_end < 0:
        raise RuntimeError("Recent achievements section not found")
    recent = group_recent_achievements(source[recent_start:recent_end + len("</section>")])

    business = BUSINESS.read_text(encoding="utf-8")
    header_end = business.find("</header>")
    footer_start = business.find("<footer>")
    if header_end < 0 or footer_start < 0:
        raise RuntimeError("Business shell could not be split")
    prefix = business[:header_end + len("</header>")]
    suffix = business[footer_start:]
    prefix = re.sub(
        r"<\?php echo \$this->element\('seo_meta', array\(.*?\)\); \?>",
        seo_block(),
        prefix,
        count=1,
        flags=re.S,
    )
    prefix = prefix.replace(
        '<li class="navi-on"><a href="business.html"><span class="en">Business</span></a></li>',
        '<li><a href="business.html"><span class="en">Business</span></a></li>',
        1,
    )
    prefix = prefix.replace(
        '<li><a href="achievements.html"><span class="en">Achievements</span></a></li>',
        '<li class="navi-on"><a href="achievements.html"><span class="en">Achievements</span></a></li>',
        1,
    )
    prefix = cache_bust(prefix)
    prefix = prefix.replace(
        '<link href="css/style.css?v=20260730a" rel="stylesheet">',
        '<link href="css/style.css?v=20260730a" rel="stylesheet">\n'
        '<link href="css/recent_achievements.css?v=20260730a" rel="stylesheet">',
        1,
    )

    recovered = json.loads(RECOVERED.read_text(encoding="utf-8"))
    by_year = {int(item["year"]): item for item in recovered}
    required = set(range(2006, 2019))
    if set(by_year) != required:
        raise RuntimeError(f"Recovered year set mismatch: {sorted(by_year)}")

    years = list(range(2026, 2005, -1))
    category_links = "\n".join(
        f'            <li><a href="#achievements-{year}">{year}年</a></li>' for year in years
    )
    archives = []
    for year in range(2018, 2005, -1):
        archive_html = group_archive_achievements(by_year[year]["html"])
        archives.append(f"""      <details class="achievement-year achievement-year--archive" id="achievements-{year}" open>
        <summary class="achievement-year__summary">
          <span class="achievement-year__number">{year}</span>
          <span class="achievement-year__toggle" aria-hidden="true"></span>
        </summary>
        <div class="achievement-year__body achievement-year__body--archive">
          {archive_html}
        </div>
      </details>""")

    banner = """

<div id="banner1">
  <div id="midashi_h2" class="h2_bg">
    <div class="container-fluid">
      <div class="yohaku">
        <h1 data-aos="fade-up"><span>Achievements</span>実績一覧</h1>
        <p class="pankuzu"><a href="/">Home</a>&nbsp;&nbsp;&gt;&nbsp;&nbsp;Achievements</p>
      </div>
    </div>
  </div>
</div>
"""
    main = f"""
<main>
  <div class="content_pd achievements-content">
    <div class="container-fluid">
      <div class="yohaku">
        <div class="achievements-layout">
          <div class="achievements-main">
{recent}
{chr(10).join(archives)}
          </div>
          <aside class="achievements-sidebar" aria-label="実績の年度一覧">
            <nav class="achievements-category">
              <h2>Category</h2>
              <ul>
{category_links}
              </ul>
            </nav>
          </aside>
        </div>
      </div>
    </div>
  </div>
</main>
"""
    script = r"""
<script>
(function () {
  function openYear(hash, shouldScroll) {
    if (!hash || hash.indexOf('#achievements-') !== 0) return;
    var target = document.querySelector(hash);
    if (!target) return;
    target.open = true;
    if (shouldScroll) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  document.addEventListener('click', function (event) {
    var link = event.target.closest('.achievements-category a');
    if (!link) return;
    event.preventDefault();
    history.replaceState(null, '', link.hash);
    openYear(link.hash, true);
  });
  openYear(location.hash, false);
}());
</script>
"""
    suffix = suffix.replace("</body>", script + "\n</body>", 1)
    page = prefix + banner + main + suffix
    if page.count("<header>") != 1 or page.count("<footer>") != 1:
        raise RuntimeError("Achievements must have one header and one footer")
    for year in years:
        if f'id="achievements-{year}"' not in page:
            raise RuntimeError(f"Achievements year missing: {year}")
    write_text(ACHIEVEMENTS, page)

    css = ACHIEVEMENTS_CSS.read_text(encoding="utf-8")
    marker = "/* 2026-07-28: independent Achievements page"
    if marker not in css:
        css = css.rstrip() + ACHIEVEMENTS_LAYOUT_CSS
    write_text(ACHIEVEMENTS_CSS, css)
    write_text(SEO_ACHIEVEMENTS_CSS, css)


def prepare_routes_and_sitemap() -> None:
    routes = ROUTES.read_text(encoding="utf-8")
    marker = "// 旧実績URLを独立したAchievementsページの各年へ恒久転送"
    if marker not in routes:
        redirects = {
            21: 2018, 20: 2017, 19: 2016, 18: 2015, 17: 2014, 16: 2013,
            15: 2012, 14: 2011, 6: 2010, 5: 2009, 7: 2008, 13: 2007, 12: 2006,
        }
        lines = [marker]
        for category_id, year in redirects.items():
            lines.append(
                f"Router::redirect('/company/index/{category_id}', '/achievements.html#achievements-{year}', array('status' => 301));"
            )
        anchor = "Router::connect('/artist.html', array('controller' => 'artist', 'action' => 'index'));"
        routes = routes.replace(anchor, anchor + "\n\n" + "\n".join(lines), 1)
    write_text(ROUTES, routes)

    sitemap = SITEMAP.read_text(encoding="utf-8")
    sitemap = re.sub(
        r"\s*<url>\s*<loc>https://www\.musician\.co\.jp/company/index/\d+</loc>.*?</url>",
        "",
        sitemap,
        flags=re.S,
    )
    sitemap = re.sub(r"<lastmod>[^<]+</lastmod>", "<lastmod>2026-07-30</lastmod>", sitemap)

    sitemap = sitemap.replace(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        1,
    )
    sitemap = re.sub(
        r"\s*<!-- works-image-gallery:start -->.*?<!-- works-image-gallery:end -->",
        "",
        sitemap,
        flags=re.S,
    )
    works_template = (WORKS / "app/View/catalog/cl01_2/default/index.html").read_text(encoding="utf-8")
    gallery_photos = re.findall(
        r"array\('image' => '([^']+)', 'category' => '([^']+)', 'title' => '([^']+)', 'alt' => '([^']+)'\),",
        works_template,
    )
    image_lines = ["    <!-- works-image-gallery:start -->"]
    for image_key, _category, _title, _alt in gallery_photos:
        image_lines.extend(
            (
                "    <image:image>",
                f"      <image:loc>https://www.musician.co.jp/images/works/gallery/{xml_escape(image_key)}-large.jpg</image:loc>",
                "    </image:image>",
            )
        )
    image_lines.append("    <!-- works-image-gallery:end -->")
    works_images = "\n".join(image_lines)
    sitemap = re.sub(
        r"(<url>\s*<loc>https://www\.musician\.co\.jp/works\.html</loc>.*?)(\s*</url>)",
        rf"\1\n{works_images}\2",
        sitemap,
        count=1,
        flags=re.S,
    )
    write_text(SITEMAP, sitemap)


def cache_bust_public_pages() -> None:
    files = [
        BUSINESS,
        WORKS / "app/View/catalog/cl01_2/default/index.html",
        SEO / "app/webroot/contact.html",
        SEO / "app/View/Contact/msg.html",
        SEO / "app/View/Contact/thanks.html",
    ]
    for path in files:
        if path.exists():
            write_text(path, cache_bust_images(cache_bust(path.read_text(encoding="utf-8"))))


def refresh_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = SEO / entry["path"]
        if not path.is_file():
            continue
        payload = path.read_bytes()
        entry["bytes"] = len(payload)
        entry["sha256"] = hashlib.sha256(payload).hexdigest()
    manifest["generated_at_jst"] = "2026-07-30"
    manifest["file_count"] = len(manifest["files"])
    write_text(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def prepare_static_preview() -> None:
    """Overlay the reviewed assets onto the existing local browser preview."""
    public = ROOT / "temporary_preview_site" / "public"
    if not public.is_dir():
        return
    (public / "css").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(STYLE, public / "css/style.css")
    shutil.copyfile(ACHIEVEMENTS_CSS, public / "css/recent_achievements.css")
    if (public / "about.html").is_file():
        shutil.copyfile(public / "about.html", public / "company.html")
        preview_company = public / "company.html"
        company_html = preview_company.read_text(encoding="utf-8")
        if 'name="robots" content="noindex, nofollow"' not in company_html:
            company_html = company_html.replace(
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                '<meta name="robots" content="noindex, nofollow">',
                1,
            )
            write_text(preview_company, company_html)
    shutil.copyfile(
        ARTIST / "app/webroot/css/artist_megumi.css",
        public / "css/artist_megumi.css",
    )
    shutil.copytree(
        WORKS / "app/webroot/images/works",
        public / "images/works",
        dirs_exist_ok=True,
    )
    staging_gallery = ROOT / "work/release_upload/5_works_gallery/app/webroot/images/works/gallery"
    staging_gallery.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        WORKS / "app/webroot/images/works/gallery",
        staging_gallery,
        dirs_exist_ok=True,
    )
    shutil.copytree(
        ARTIST / "app/webroot/images/artists",
        public / "images/artists",
        dirs_exist_ok=True,
    )
    for name in (
        "megumi-portrait-card.jpg",
        "company_photo_megumi.jpg",
        "company_photo_miyazaki_illustration.jpg",
    ):
        shutil.copyfile(WORKS / "app/webroot/images" / name, public / "images" / name)

    # Browsers ignore server-side SEO blocks in production, so remove them from
    # local file previews while keeping the production files untouched.
    for source, destination in (
        (SEO / "app/View/Homes/index.html", public / "home.html"),
        (ACHIEVEMENTS, public / "achievements.html"),
        (BUSINESS, public / "business.html"),
        (COMPANY, public / "about.html"),
    ):
        text = re.sub(r"<\?php.*?\?>", "", source.read_text(encoding="utf-8"), flags=re.S)
        if 'name="robots" content="noindex, nofollow"' not in text:
            text = text.replace(
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                '<meta name="robots" content="noindex, nofollow">',
                1,
            )
        write_text(destination, text)


def validate() -> None:
    company = COMPANY.read_text(encoding="utf-8")
    artist_list = (ARTIST / "app/View/catalog/cl02_4/default/index.html").read_text(encoding="utf-8")
    artist_view = (ARTIST / "app/View/catalog/cl02_4/default/view.html").read_text(encoding="utf-8")
    achievements = ACHIEVEMENTS.read_text(encoding="utf-8")
    required_company = ("代表取締役</span> 大町めぐみ", "プロデューサー</span> 宮﨑 隆", "company_photo_miyazaki_illustration.jpg")
    if not all(item in company for item in required_company):
        raise RuntimeError("About us approved profiles are incomplete")
    if "recent-achievements" in company or "Career" in company:
        raise RuntimeError("About us contains removed content")
    if "$artistId === 62" not in artist_list or "所属アーティスト" not in artist_list:
        raise RuntimeError("Megumi affiliation rule is missing")
    if "kZvvnMDZHXU" not in artist_view or "2年間" not in artist_view:
        raise RuntimeError("Megumi detail page is incomplete")
    if achievements.count("achievement-year") < 21:
        raise RuntimeError("Achievements year archive is incomplete")
    prohibited = "株式会社MUSICIAN"
    public = "\n".join((company, artist_list, artist_view, achievements))
    if prohibited in public:
        raise RuntimeError("Prohibited company name found")


def main() -> None:
    prepare_style()
    prepare_company()
    sync_artist()
    prepare_achievements()
    prepare_routes_and_sitemap()
    cache_bust_public_pages()
    refresh_manifest()
    prepare_static_preview()
    validate()
    print("Recovered release prepared and validated.")


if __name__ == "__main__":
    main()
