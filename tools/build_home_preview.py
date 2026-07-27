from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "new_site" / "seo_deployment" / "app" / "View" / "Homes" / "index.html"
DESTINATION = ROOT / "temporary_preview_site" / "public" / "home.html"

PREVIEW_META = """<title>MUSICIAN トップページ｜公開前確認</title>
<meta name="description" content="MUSICIANトップページ全体の公開前確認用プレビューです。">
<meta name="robots" content="noindex, nofollow">"""

ARTIST_PLACEHOLDER = """<div class="home-preview-artist-note" role="note">
  <strong>アーティスト欄</strong>
  <p>公開時はCMSで選択されたアーティストを表示します。ここでは見出し、余白、配色、Artistページへの導線を確認できます。</p>
</div>"""

PREVIEW_NOTICE = """<div class="home-preview-notice" role="note"><span>PRIVATE PREVIEW</span>トップページ全体確認用：Worksは承認済み6テーマ・ロゴ処理済み画像へ統一</div>"""

PREVIEW_STYLE = """<style>
.home-preview-notice{background:#041e42;color:#fff;font-family:"Shippori Mincho",serif;font-size:12px;font-weight:600;letter-spacing:.08em;padding:9px 18px;text-align:center}
.home-preview-notice span{color:#fbe1bd;font-family:"Urbanist",sans-serif;font-weight:800;letter-spacing:.18em;margin-right:12px}
.home-preview-artist-note{border:1px solid rgba(251,225,189,.55);color:#fbe1bd;margin:0 auto 28px;max-width:760px;padding:28px;text-align:center}
.home-preview-artist-note strong{font-family:"Urbanist",sans-serif;letter-spacing:.12em}
.home-preview-artist-note p{margin:10px 0 0}
@media(max-width:767px){.home-preview-notice{font-size:10px}.home-preview-notice span{display:block;margin:0 0 2px}}
</style>"""


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    if text.count(start) != 1:
        raise RuntimeError(f"{label}: expected one start marker, found {text.count(start)}")
    start_at = text.index(start)
    end_at = text.index(end, start_at) + len(end)
    return text[:start_at] + replacement + text[end_at:]


def build() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    text = replace_between(
        text,
        "<?php echo $this->element('seo_meta'",
        ")); ?>",
        PREVIEW_META,
        "preview metadata",
    )
    text = replace_between(
        text,
        "<?php $boxes = $this->requestAction(array('controller'=>'artist'",
        "<?php endforeach; ?>",
        ARTIST_PLACEHOLDER,
        "artist CMS placeholder",
    )
    text = text.replace("</head>", PREVIEW_STYLE + chr(10) + "</head>", 1)
    text = text.replace("<body>", "<body>" + chr(10) + PREVIEW_NOTICE, 1)
    if "<?php" in text or "?>" in text:
        raise RuntimeError("unprocessed PHP remains in homepage preview")
    DESTINATION.write_text(text, encoding="utf-8", newline=chr(10))
    print(f"Built {DESTINATION.relative_to(ROOT)}")


if __name__ == "__main__":
    build()