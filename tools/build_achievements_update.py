#!/usr/bin/env python3
"""Build the staged MUSICIAN achievements update and a static local preview.

The source backup is treated as immutable. Generated deployment files are written
under new_site/deployment and the browser preview under new_site/preview.
"""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "new_site" / "data" / "achievements_recent.json"
SOURCE_TEMPLATE = (
    ROOT
    / "backup_2026-07-25"
    / "site_files"
    / "app"
    / "View"
    / "catalog"
    / "cl01_3"
    / "default"
    / "index.html"
)
SOURCE_WEBROOT = ROOT / "backup_2026-07-25" / "site_files" / "app" / "webroot"
LIVE_HTML = ROOT / "work" / "current_company_live_raw.html"

DEPLOY_TEMPLATE = (
    ROOT
    / "new_site"
    / "deployment"
    / "app"
    / "View"
    / "catalog"
    / "cl01_3"
    / "default"
    / "index.html"
)
DEPLOY_CSS = (
    ROOT
    / "new_site"
    / "deployment"
    / "app"
    / "webroot"
    / "css"
    / "recent_achievements.css"
)
PREVIEW_DIR = ROOT / "new_site" / "preview"
PREVIEW_HTML = PREVIEW_DIR / "company.html"
PREVIEW_CSS = PREVIEW_DIR / "css" / "recent_achievements.css"

CSS_LINK_ANCHOR = '<link href="css/sidemenu2.css" rel="stylesheet"><!--サイドメニュー-->'
CSS_LINK = (
    CSS_LINK_ANCHOR
    + '\n<link href="css/recent_achievements.css" rel="stylesheet">'
    + '<!--近年の実績-->'
)

SIDEBAR_ANCHOR = """                                    <ul>
                                        <?php foreach($category_all as $category_id => $category):?>"""
SIDEBAR_REPLACEMENT = """                                    <ul>
                                        <li><a href="achievements.html#achievements-2026">2026年</a></li>
                                        <li><a href="achievements.html#achievements-2025">2025年</a></li>
                                        <li><a href="achievements.html#achievements-2024">2024年</a></li>
                                        <li><a href="achievements.html#achievements-2023">2023年</a></li>
                                        <li><a href="achievements.html#achievements-2022">2022年</a></li>
                                        <li><a href="achievements.html#achievements-2021">2021年</a></li>
                                        <li><a href="achievements.html#achievements-2020">2020年</a></li>
                                        <li><a href="achievements.html#achievements-2019">2019年</a></li>
                                        <?php foreach($category_all as $category_id => $category):?>"""

TEMPLATE_CONTENT_ANCHOR = """<h4 class="midashi3 mb30_md50"><?php echo $target['title'];?></h4>"""
PREVIEW_CONTENT_ANCHOR = '<h4 class="midashi3 mb30_md50">2018年</h4>'


CSS = r"""
/* 2019年以降の実績。既存テーマの色・書体に合わせた追加スタイル。 */
.recent-achievements {
  --ma-navy: #041e42;
  --ma-orange: #e36927;
  --ma-beige: #fbe1bd;
  color: var(--ma-navy);
  margin: 0 0 72px;
}

.recent-achievements * {
  box-sizing: border-box;
}


.achievement-archive-heading__eyebrow {
  color: var(--ma-orange);
  font-family: "Urbanist", sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: .15em;
  margin: 0 0 7px;
  text-transform: uppercase;
}


.achievement-year {
  border-bottom: 1px solid rgba(4, 30, 66, .22);
}

.achievement-year:first-child {
  border-top: 1px solid rgba(4, 30, 66, .22);
}

.achievement-year__summary {
  align-items: center;
  cursor: pointer;
  display: grid;
  gap: 18px;
  grid-template-columns: 1fr 32px;
  list-style: none;
  min-height: 92px;
  padding: 18px 4px;
}

.achievement-year__summary::-webkit-details-marker {
  display: none;
}

.achievement-year__number {
  color: var(--ma-navy);
  font-family: "Urbanist", sans-serif;
  font-size: clamp(31px, 4vw, 43px);
  font-weight: 800;
  letter-spacing: .02em;
  line-height: 1;
}


.achievement-year__toggle {
  border: 1px solid rgba(4, 30, 66, .3);
  border-radius: 50%;
  height: 30px;
  position: relative;
  width: 30px;
}

.achievement-year__toggle::before,
.achievement-year__toggle::after {
  background: var(--ma-orange);
  content: "";
  height: 1px;
  left: 7px;
  position: absolute;
  top: 14px;
  transition: transform .22s ease;
  width: 14px;
}

.achievement-year__toggle::after {
  transform: rotate(90deg);
}

.achievement-year[open] .achievement-year__toggle::after {
  transform: rotate(0);
}

.achievement-year__body {
  padding: 0 4px 34px;
}


.achievement-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.achievement-list__item {
  align-items: start;
  border-top: 1px dotted rgba(4, 30, 66, .24);
  display: grid;
  gap: 14px 18px;
  grid-template-columns: 140px minmax(0, 1fr);
  padding: 17px 0 18px;
}

.achievement-list__item:first-child {
  border-top: 0;
  padding-top: 4px;
}


.achievement-list__category {
  border: 1px solid rgba(227, 105, 39, .55);
  color: #b34c18;
  display: inline-block;
  font-size: 11px;
  line-height: 1.45;
  padding: 4px 7px;
  text-align: center;
}

.achievement-list__title {
  font-size: 16px;
  line-height: 1.65;
  margin: 0;
}

.achievement-list__detail {
  font-size: 13px;
  line-height: 1.7;
  margin: 4px 0 0;
  opacity: .75;
}


.achievement-archive-heading {
  border-top: 4px solid var(--ma-navy, #041e42);
  margin: 0 0 38px;
  padding-top: 25px;
}

.achievement-archive-heading h4 {
  font-size: 25px;
  margin: 0;
}

@media (max-width: 767.98px) {
  .recent-achievements {
    margin-bottom: 54px;
  }


  .achievement-year__summary {
    gap: 10px;
    grid-template-columns: 1fr 30px;
    min-height: 78px;
  }

  .achievement-list__item {
    gap: 7px 10px;
    grid-template-columns: 1fr;
    padding: 15px 0 16px;
  }

  .achievement-list__category {
    justify-self: start;
  }


}

@media (prefers-reduced-motion: reduce) {
  .achievement-year__toggle::before,
  .achievement-year__toggle::after {
    transition: none;
  }
}
""".strip() + "\n"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_recent(data: dict) -> str:
    chunks = [
        '<section class="recent-achievements" aria-label="2019年から2026年の実績">',
        '  <div class="recent-achievements__years">',
    ]

    for index, year in enumerate(data["years"]):
        is_open = " open"

        chunks.extend(
            [
                f'    <details class="achievement-year" id="achievements-{esc(year["year"])}"{is_open}>',
                '      <summary class="achievement-year__summary">',
                f'        <span class="achievement-year__number">{esc(year["year"])}</span>',

                '        <span class="achievement-year__toggle" aria-hidden="true"></span>',
                '      </summary>',
                '      <div class="achievement-year__body">',
            ]
        )

        chunks.append('        <ul class="achievement-list">')
        for entry in year["entries"]:
            chunks.extend(
                [
                    '          <li class="achievement-list__item">',

                    f'            <span class="achievement-list__category">{esc(entry["category"])}</span>',
                    '            <div class="achievement-list__content">',
                    f'              <p class="achievement-list__title">{esc(entry["title"])}</p>',
                    f'              <p class="achievement-list__detail">{esc(entry["detail"])}</p>',
                    '            </div>',
                    '          </li>',
                ]
            )
        chunks.extend(
            [
                '        </ul>',
                '      </div>',
                '    </details>',
            ]
        )

    chunks.extend(
        [
            '  </div>',

            '</section>',
            '<div class="achievement-archive-heading">',
            '  <p class="achievement-archive-heading__eyebrow">Archive</p>',
            '  <h4>2018年以前の実績</h4>',
            '</div>',
        ]
    )
    return "\n".join(chunks)


def replace_once(text: str, anchor: str, replacement: str, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"Expected one {label} anchor, found {count}")
    return text.replace(anchor, replacement, 1)


def copy_preview_assets() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for folder in ("css", "images", "js"):
        source = SOURCE_WEBROOT / folder
        target = PREVIEW_DIR / folder
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    for filename in ("favicon.png", "apple-touch-icon.png"):
        source = SOURCE_WEBROOT / filename
        if source.exists():
            shutil.copy2(source, PREVIEW_DIR / filename)


def build() -> None:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    recent_html = render_recent(data)

    template = SOURCE_TEMPLATE.read_text(encoding="utf-8")
    template = replace_once(template, CSS_LINK_ANCHOR, CSS_LINK, "CSS link")
    template = replace_once(template, SIDEBAR_ANCHOR, SIDEBAR_REPLACEMENT, "sidebar")
    template_recent = (
        "<?php if ((int)$target_id === 21): ?>\n"
        + recent_html
        + "\n<?php endif; ?>\n\n"
        + TEMPLATE_CONTENT_ANCHOR
    )
    template = replace_once(
        template, TEMPLATE_CONTENT_ANCHOR, template_recent, "template content"
    )
    DEPLOY_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    DEPLOY_TEMPLATE.write_text(template, encoding="utf-8", newline="\n")

    DEPLOY_CSS.parent.mkdir(parents=True, exist_ok=True)
    DEPLOY_CSS.write_text(CSS, encoding="utf-8", newline="\n")

    copy_preview_assets()
    preview = LIVE_HTML.read_text(encoding="utf-8")
    preview_css_anchor = '<link href="css/sidemenu2.css" rel="stylesheet"><!--サイドメニュー-->'
    preview = replace_once(
        preview,
        preview_css_anchor,
        preview_css_anchor
        + '\n<link href="css/recent_achievements.css" rel="stylesheet">',
        "preview CSS link",
    )
    preview = replace_once(
        preview,
        PREVIEW_CONTENT_ANCHOR,
        recent_html + "\n" + PREVIEW_CONTENT_ANCHOR,
        "preview content",
    )
    PREVIEW_HTML.write_text(preview, encoding="utf-8", newline="\n")
    PREVIEW_CSS.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_CSS.write_text(CSS, encoding="utf-8", newline="\n")

    print(f"Built {DEPLOY_TEMPLATE}")
    print(f"Built {DEPLOY_CSS}")
    print(f"Built {PREVIEW_HTML}")


if __name__ == "__main__":
    build()
