#!/usr/bin/env python3
"""Build the approved Asakusa Taikoban Artist page and web assets."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE_GROUP = Path(r"A:\Users\Takashi Miyazaki\Downloads\1feaf1cd-e580-4d20-b7f1-2ad12c851808.jpg")
SOURCE_PERFORMANCE = Path(r"A:\Users\Takashi Miyazaki\Downloads\1a04ec78-ac98-465f-9ab2-b8ba5e95f3bb.jpg")
OUTPUT_ROOTS = (
    ROOT / "new_site/artist_deployment/app/webroot",
    ROOT / "temporary_preview_site/public",
)
ASSET_VERSION = "20260728d"


SEO_BLOCK = """<?php echo $this->element('seo_meta', array(
  'seoTitle' => '浅草たいこばん｜Japanese Taiko Performance・和太鼓演奏依頼｜MUSICIAN',
  'seoDescription' => '東京・浅草を拠点に活動する和太鼓団体「浅草たいこばん（Asakusa Taikoban）」。企業イベント、式典、ホテル、インバウンド向け公演など、会場に合わせたJapanese taiko drumming performanceをご提案します。',
  'seoCanonicalPath' => '/artist-asakusa-taikoban.html',
  'seoPageType' => 'ProfilePage',
  'seoImage' => '/images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg?v=20260728d',
  'seoBreadcrumbItems' => array(
    array('name' => 'ホーム', 'item' => '/'),
    array('name' => 'アーティスト', 'item' => '/artist.html'),
    array('name' => '浅草たいこばん', 'item' => '/artist-asakusa-taikoban.html')
  ),
  'seoAdditionalSchema' => array(
    array(
      '@type' => 'MusicGroup',
      '@id' => 'https://www.musician.co.jp/artist-asakusa-taikoban.html#artist',
      'name' => '浅草たいこばん',
      'alternateName' => 'Asakusa Taikoban',
      'genre' => array('和太鼓', '日本伝統音楽'),
      'image' => 'https://www.musician.co.jp/images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg?v=20260728d',
      'url' => 'https://www.musician.co.jp/artist-asakusa-taikoban.html',
      'memberOf' => array('@id' => 'https://www.musician.co.jp/#organization')
    ),
    array(
      '@type' => 'VideoObject',
      'name' => '浅草たいこばん 和太鼓演奏',
      'description' => '和太鼓団体「浅草たいこばん」の演奏映像。',
      'thumbnailUrl' => 'https://i.ytimg.com/vi/Vp875mBKNOU/maxresdefault.jpg',
      'embedUrl' => 'https://www.youtube-nocookie.com/embed/Vp875mBKNOU',
      'contentUrl' => 'https://youtu.be/Vp875mBKNOU'
    )
  )
)); ?>"""

PREVIEW_SEO_BLOCK = """<title>浅草たいこばん｜Japanese Taiko Performance・和太鼓演奏依頼｜MUSICIAN</title>
<meta name="description" content="東京・浅草を拠点に活動する和太鼓団体『浅草たいこばん（Asakusa Taikoban）』。企業イベント、式典、ホテル、インバウンド向け公演など、会場に合わせた和太鼓演奏をご提案します。">"""


MAIN = """
<main>
<article class="taikoban-profile" id="artist">
  <section class="taikoban-hero" aria-labelledby="taikoban-name">
    <div class="taikoban-hero__image">
      <img src="images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg?v=20260728d" alt="浅草寺の雷門を背景に並ぶ和太鼓団体 浅草たいこばんの5名" width="1200" height="900" fetchpriority="high">
    </div>
    <div class="taikoban-hero__content">
      <p class="taikoban-eyebrow">JAPANESE TAIKO PERFORMANCE</p>
      <p class="taikoban-role">和太鼓団体</p>
      <h2 id="taikoban-name">浅草たいこばん<span>Asakusa Taikoban</span></h2>
      <p class="taikoban-lead">浅草の祭りの高揚感と江戸の粋を、現代のステージへ。力強い響きと息の合った演奏で、会場を一体感のある特別な空間へ変えます。</p>
      <a class="taikoban-button" href="contact.html">出演・演奏を相談する</a>
    </div>
  </section>

  <section class="taikoban-section" aria-labelledby="taikoban-profile-title">
    <div class="taikoban-section__heading">
      <p>PROFILE</p>
      <h2 id="taikoban-profile-title">浅草から届ける、和太鼓の力と粋</h2>
    </div>
    <div class="taikoban-copy">
      <p>「浅草たいこばん」は、東京・浅草を拠点に活動する和太鼓団体です。伝統的な和太鼓の力強さを大切にしながら、舞台の見せ方や構成にも工夫を重ね、祭りの高揚感と江戸の粋を感じさせる演奏を届けています。</p>
      <p>豊富な舞台経験を持つ奏者による、息の合ったダイナミックな演奏が持ち味です。身体に響く重低音から繊細なリズムワークまで、視覚と聴覚の両方で楽しめるステージをつくります。</p>
      <p>企業イベント、式典、ホテル・商業施設、インバウンド向け公演、地域フェスティバルなど、さまざまな場面に対応します。会場の広さや催事の目的、持ち時間に合わせて編成と演出を調整できるため、オープニングの短い演奏から、見応えのあるステージまでご相談いただけます。</p>
      <p>単に楽曲を演奏するだけでなく、日本文化の魅力を分かりやすく、心に残るかたちで伝えることを大切にしています。海外からのお客様を迎える催しや、イベントに力強い印象を加えたい場面にも適した和太鼓パフォーマンスです。</p>
    </div>
  </section>

  <section class="taikoban-section taikoban-section--english" lang="en" aria-labelledby="taikoban-english-title">
    <div class="taikoban-section__heading">
      <p>ENGLISH PROFILE</p>
      <h2 id="taikoban-english-title">Japanese Taiko Drumming from the Heart of Asakusa</h2>
    </div>
    <div class="taikoban-copy taikoban-copy--english">
      <p>Asakusa Taikoban is a professional Japanese taiko drumming group based in Asakusa, Tokyo—one of Japan’s most iconic cultural districts. The ensemble brings together the powerful sound of traditional Japanese drums, the energy of local festivals, and a polished stage presentation inspired by the spirit of Edo.</p>
      <p>From resonant, full-bodied beats to precise and expressive rhythmic passages, the performers create an engaging experience for both the eyes and ears. Programs can be adapted to the venue, event concept, running time, and audience.</p>
      <p>Performances are available for corporate events, opening ceremonies, anniversary celebrations, hotels, commercial facilities, international receptions, inbound tourism programs, cultural festivals, and seasonal events. Short opening performances and full stage programs can both be arranged.</p>
      <p>For international guests, Asakusa Taikoban offers an accessible and memorable introduction to Japanese culture through live taiko performance. MUSICIAN can also coordinate staging, sound, event flow, and other production requirements.</p>
    </div>
  </section>

  <section class="taikoban-section taikoban-section--scenes" aria-labelledby="taikoban-scenes-title">
    <div class="taikoban-section__heading">
      <p>PERFORMANCE</p>
      <h2 id="taikoban-scenes-title">主な出演・演奏シーン</h2>
    </div>
    <ul class="taikoban-scenes">
      <li>浅草地域イベント・商店街催事</li>
      <li>国内外の観光客に向けたステージ</li>
      <li>企業パーティー・周年記念イベント</li>
      <li>ホテル・商業施設での特別公演</li>
      <li>地域フェスティバル・夏祭り・季節イベント</li>
      <li>文化イベント・式典のオープニング演奏</li>
    </ul>
  </section>

  <section class="taikoban-section taikoban-section--visual" aria-labelledby="taikoban-gallery-title">
    <div class="taikoban-section__heading">
      <p>GALLERY</p>
      <h2 id="taikoban-gallery-title">演奏イメージ</h2>
    </div>
    <div class="taikoban-gallery">
      <a href="images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg?v=20260728d" target="_blank" rel="noopener noreferrer">
        <img src="images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg?v=20260728d" alt="浅草を拠点に活動する和太鼓団体 浅草たいこばんの集合写真" width="1200" height="900" loading="lazy" decoding="async">
      </a>
      <a href="images/artists/asakusa-taikoban/asakusa-taikoban-performance.jpg?v=20260728d" target="_blank" rel="noopener noreferrer">
        <img src="images/artists/asakusa-taikoban/asakusa-taikoban-performance.jpg?v=20260728d" alt="海辺で大太鼓と長胴太鼓を演奏する浅草たいこばん" width="1200" height="1600" loading="lazy" decoding="async">
      </a>
    </div>
  </section>

  <section class="taikoban-section taikoban-section--video" aria-labelledby="taikoban-video-title">
    <div class="taikoban-section__heading">
      <p>MOVIE</p>
      <h2 id="taikoban-video-title">演奏映像</h2>
    </div>
    <div class="taikoban-video">
      <div class="taikoban-video__frame">
        <iframe src="https://www.youtube-nocookie.com/embed/Vp875mBKNOU?rel=0" title="浅草たいこばん 和太鼓演奏" loading="lazy" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
      </div>
      <p><a href="https://youtu.be/Vp875mBKNOU" target="_blank" rel="noopener noreferrer">YouTubeで見る</a></p>
    </div>
  </section>

  <section class="taikoban-booking" aria-labelledby="taikoban-booking-title">
    <div>
      <p>BOOKING &amp; PRODUCTION</p>
      <h2 id="taikoban-booking-title">催事の目的と会場に合わせてご提案します</h2>
      <p>編成、演奏時間、進行との組み合わせ、音響や舞台運営まで、MUSICIANがまとめてご相談を承ります。まだ内容が決まっていない段階でもお気軽にお問い合わせください。</p>
      <a class="taikoban-button taikoban-button--light" href="contact.html">浅草たいこばんへの出演依頼</a>
    </div>
  </section>
</article>
</main>
"""


CSS = """.taikoban-profile{--navy:#041e42;--blue:#0b3d73;--pale:#eef3f8;--gold:#c99a45;color:var(--navy);font-family:\"Shippori Mincho\",serif;font-weight:600;letter-spacing:.035em;background:#fff}.taikoban-profile *{box-sizing:border-box}.taikoban-hero{background:var(--navy);color:#fff;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr);min-height:650px}.taikoban-hero__image{min-height:650px;overflow:hidden}.taikoban-hero__image img{display:block;height:100%;object-fit:cover;object-position:center;width:100%}.taikoban-hero__content{align-self:center;padding:70px clamp(36px,6vw,105px)}.taikoban-eyebrow,.taikoban-section__heading>p,.taikoban-booking>div>p:first-child{font-family:\"Urbanist\",sans-serif;font-size:13px;letter-spacing:.22em;margin:0 0 15px}.taikoban-role{color:#d8e7f5;font-size:17px;margin:0 0 8px}.taikoban-hero h2{color:#fff;font-size:clamp(38px,4.2vw,68px);line-height:1.2;margin:0 0 28px}.taikoban-hero h2 span{display:block;font-family:\"Urbanist\",sans-serif;font-size:14px;letter-spacing:.18em;margin-top:12px}.taikoban-lead{font-size:16px;line-height:2;margin:0 0 34px}.taikoban-button{background:#fff;color:var(--navy)!important;display:inline-block;font-size:14px;padding:16px 28px;text-decoration:none!important}.taikoban-button:hover{background:#dce8f3}.taikoban-section{display:grid;gap:clamp(34px,6vw,90px);grid-template-columns:minmax(190px,.34fr) minmax(0,1fr);margin:0 auto;max-width:1500px;padding:100px clamp(24px,7vw,120px)}.taikoban-section__heading h2{font-size:clamp(28px,3vw,42px);line-height:1.45;margin:0}.taikoban-copy{columns:2;column-gap:44px}.taikoban-copy p{break-inside:avoid;font-size:15px;line-height:2.1;margin:0 0 22px}.taikoban-section--scenes{background:var(--pale);max-width:none}.taikoban-scenes{display:grid;gap:0;grid-template-columns:repeat(2,minmax(0,1fr));list-style:none;margin:0;padding:0}.taikoban-scenes li{border-top:1px solid rgba(4,30,66,.18);font-size:14px;line-height:1.8;padding:18px 20px 18px 30px;position:relative}.taikoban-scenes li::before{background:var(--gold);content:\"\";height:7px;left:8px;position:absolute;top:27px;transform:rotate(45deg);width:7px}.taikoban-section--visual{max-width:1500px}.taikoban-gallery{display:grid;gap:16px;grid-template-columns:1.55fr .85fr}.taikoban-gallery a{background:var(--pale);display:block;overflow:hidden}.taikoban-gallery img{display:block;height:100%;object-fit:cover;width:100%}.taikoban-gallery a:first-child img{aspect-ratio:4/3}.taikoban-gallery a:last-child img{aspect-ratio:3/4;object-position:center}.taikoban-section--video{background:var(--pale);max-width:none}.taikoban-video__frame{aspect-ratio:16/9;background:#000;overflow:hidden;width:100%}.taikoban-video iframe{border:0;display:block;height:100%;width:100%}.taikoban-video p{font-size:13px;margin:14px 0 0}.taikoban-video a{color:var(--blue)}.taikoban-booking{background:var(--navy);color:#fff;padding:90px clamp(24px,14vw,250px);text-align:center}.taikoban-booking h2{color:#fff;font-size:clamp(28px,3vw,42px);line-height:1.5;margin:0 0 24px}.taikoban-booking p{font-size:15px;line-height:2;margin:0 auto 28px;max-width:920px}.taikoban-button--light{margin-top:8px}
.taikoban-section--english{border-top:1px solid rgba(4,30,66,.12);font-family:\"Urbanist\",sans-serif;font-weight:500}.taikoban-section--english .taikoban-section__heading h2{font-family:\"Urbanist\",sans-serif;font-weight:600;letter-spacing:.025em}.taikoban-copy--english p{font-size:15px;letter-spacing:.015em;line-height:1.9}
@media(max-width:991px){.taikoban-hero{grid-template-columns:1fr}.taikoban-hero__image{min-height:0}.taikoban-hero__image img{height:auto}.taikoban-hero__content{padding:60px 8vw 72px}.taikoban-section{grid-template-columns:1fr;padding-bottom:78px;padding-top:78px}.taikoban-copy{columns:1}}
@media(max-width:575px){.taikoban-hero__content{padding:42px 24px 56px}.taikoban-hero h2{font-size:39px}.taikoban-lead{font-size:14px}.taikoban-section{gap:28px;padding:58px 20px}.taikoban-scenes{grid-template-columns:1fr}.taikoban-gallery{grid-template-columns:1fr}.taikoban-gallery a:last-child img{aspect-ratio:4/3;object-position:center 38%}.taikoban-booking{padding:62px 20px}}
"""


def save_jpeg(source: Path, destination: Path, size: tuple[int, int]) -> None:
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "JPEG", quality=88, optimize=True, progressive=True)


def build_page(reference: str) -> str:
    prefix = reference[: reference.index("<main>")]
    suffix = reference[reference.index("</main>") + len("</main>") :]
    seo_start = prefix.index("<?php echo $this->element('seo_meta'")
    seo_end = prefix.index(")); ?>", seo_start) + len(")); ?>")
    prefix = prefix[:seo_start] + SEO_BLOCK + prefix[seo_end:]
    prefix = prefix.replace(
        '<link href="css/bootstrap4-print.css" rel="stylesheet">',
        f'<link href="css/artist_taikoban.css?v={ASSET_VERSION}" rel="stylesheet">\n<link href="css/bootstrap4-print.css" rel="stylesheet">',
    )
    prefix = prefix.replace('<li class="navi-on"><a href="business.html">', '<li><a href="business.html">', 1)
    prefix = prefix.replace('<li><a href="artist.html">', '<li class="navi-on"><a href="artist.html">', 1)
    prefix = prefix.replace('<span>Business</span>事業内容', '<span>Artist</span>アーティスト', 1)
    prefix = prefix.replace('Home</a>&nbsp;&nbsp;&gt;&nbsp;&nbsp;Business', 'Home</a>&nbsp;&nbsp;&gt;&nbsp;&nbsp;<a href="artist.html">Artist</a>&nbsp;&nbsp;&gt;&nbsp;&nbsp;浅草たいこばん', 1)
    return prefix + MAIN + suffix


def main() -> int:
    for source in (SOURCE_GROUP, SOURCE_PERFORMANCE):
        if not source.is_file():
            raise FileNotFoundError(source)
    business = (ROOT / "new_site/seo_deployment/app/webroot/business.html").read_text(encoding="utf-8")
    page = build_page(business)
    preview_page = page.replace(SEO_BLOCK, PREVIEW_SEO_BLOCK, 1)
    # Older generator revisions duplicated these assets into the SEO package.
    # The reviewed Artist package is the single deployment source for them.
    obsolete_seo_root = ROOT / "new_site/seo_deployment/app/webroot"
    obsolete_paths = (
        obsolete_seo_root / "artist-asakusa-taikoban.html",
        obsolete_seo_root / "css/artist_taikoban.css",
        obsolete_seo_root / "images/artists/asakusa-taikoban/asakusa-taikoban-card.jpg",
        obsolete_seo_root / "images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg",
        obsolete_seo_root / "images/artists/asakusa-taikoban/asakusa-taikoban-performance.jpg",
    )
    for obsolete in obsolete_paths:
        if obsolete.is_file():
            obsolete.unlink()
    for directory in (
        obsolete_seo_root / "images/artists/asakusa-taikoban",
        obsolete_seo_root / "images/artists",
        obsolete_seo_root / "images",
    ):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    for output_root in OUTPUT_ROOTS:
        image_dir = output_root / "images/artists/asakusa-taikoban"
        save_jpeg(SOURCE_GROUP, image_dir / "asakusa-taikoban-group.jpg", (1200, 900))
        save_jpeg(SOURCE_GROUP, image_dir / "asakusa-taikoban-card.jpg", (800, 600))
        save_jpeg(SOURCE_PERFORMANCE, image_dir / "asakusa-taikoban-performance.jpg", (1200, 1600))
        (output_root / "css/artist_taikoban.css").write_text(CSS, encoding="utf-8", newline="\n")
        output_page = preview_page if output_root == ROOT / "temporary_preview_site/public" else page
        (output_root / "artist-asakusa-taikoban.html").write_text(output_page, encoding="utf-8", newline="\n")

    manifest_path = ROOT / "new_site/artist_deployment/asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["asakusa_taikoban"] = {
        "sources": [SOURCE_GROUP.name, SOURCE_PERFORMANCE.name],
        "page": "/artist-asakusa-taikoban.html",
        "images": [
            "images/artists/asakusa-taikoban/asakusa-taikoban-card.jpg",
            "images/artists/asakusa-taikoban/asakusa-taikoban-group.jpg",
            "images/artists/asakusa-taikoban/asakusa-taikoban-performance.jpg",
        ],
        "video": "https://youtu.be/Vp875mBKNOU",
        "metadata": "stripped by re-encoding",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Prepared Asakusa Taikoban page, CSS and 3 optimized JPEG assets for release and preview")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
