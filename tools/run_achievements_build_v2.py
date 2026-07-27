#!/usr/bin/env python3
"""Run the achievements build with normalized live-preview anchors."""

from pathlib import Path

import build_achievements_update as builder


builder.TEMPLATE_CONTENT_ANCHOR = (
    '<h4 class="midashi3 mb30_md50">'
    "<?php echo $target['title'];?></h4>"
)

preview_source = builder.ROOT / "work" / "current_company_preview_source.html"
live_html = builder.LIVE_HTML.read_text(encoding="utf-8")
live_html = live_html.replace(
    '<link href="https://www.musician.co.jp/css/sidemenu2.css" rel="stylesheet"><!--サイドメニュー-->',
    '<link href="css/sidemenu2.css" rel="stylesheet"><!--サイドメニュー-->',
    1,
)
preview_source.write_text(live_html, encoding="utf-8", newline="\n")
builder.LIVE_HTML = Path(preview_source)

builder.build()
