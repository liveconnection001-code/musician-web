"""Build the CakePHP Works release template from the current SEO template.

The Works root becomes a curated capability showcase. Existing CMS category
rendering remains available for non-root routes, but is no longer exposed from
the new root experience.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "new_site/seo_deployment/app/View/catalog/cl01_2/default/index.html"
DESTINATION = ROOT / "new_site/works_deployment/app/View/catalog/cl01_2/default/index.html"

SHOWCASE = r'''<main class="works-showcase">
<section class="works-showcase__hero" aria-labelledby="works-showcase-title">
  <picture>
    <source srcset="images/works/hero-corporate-show-clean.webp" type="image/webp">
    <img src="images/works/hero-corporate-show-clean.jpg" alt="企業イベントでライブ演奏を行う6名編成の女性バンド" width="1920" height="1080" fetchpriority="high" decoding="async">
  </picture>
  <div class="works-showcase__shade"></div>
  <div class="works-showcase__hero-content">
    <p class="works-showcase__kicker">SELECTED WORKS</p>
    <h1 id="works-showcase-title">その場にふさわしい音楽を、<br>企画から本番まで。</h1>
    <p class="works-showcase__lead">企業イベント、国際レセプション、ホテル、展示会など。<br class="works-showcase__desktop-only">目的と空間に合わせ、音楽と現場を一つにつなげます。</p>
    <a class="works-showcase__scroll" href="#selected-works">仕事を見る <span aria-hidden="true">↓</span></a>
  </div>
</section>

<section class="works-showcase__intro" id="selected-works" aria-labelledby="works-selected-heading">
  <div>
    <p class="works-showcase__kicker works-showcase__kicker--dark">WHAT WE CREATE</p>
    <h2 id="works-selected-heading">実施時期ではなく、<br>音楽でつくった体験から。</h2>
  </div>
  <p>MUSICIANが手がけるのは、出演者を編成するだけではありません。演者と音楽を核に、音響・照明はもちろん、空間の佇まい、動線、進行までを一つの表現として設計し、五感に響く音楽芸術の場を制作・演出します。</p>
</section>

<section class="works-showcase__scope" aria-labelledby="works-scope-title">
  <p class="works-showcase__kicker">ONE TEAM, END TO END</p>
  <h2 id="works-scope-title">企画・キャスティング・現場運営を、ひとつのチームで。</h2>
  <div class="works-showcase__steps">
    <div><span>01</span><strong>目的と空間を理解</strong><p>場の役割、来場者、進行、ご予算を整理します。</p></div>
    <div><span>02</span><strong>芸術体験を構想・制作</strong><p>演者、音楽、音響、照明、空間演出を一つの表現として設計します。</p></div>
    <div><span>03</span><strong>本番を成立させる</strong><p>出演準備から当日の進行まで、現場を支えます。</p></div>
  </div>
</section>

<section class="works-showcase__cta" aria-labelledby="works-cta-title">
  <p class="works-showcase__kicker works-showcase__kicker--dark">START A CONVERSATION</p>
  <h2 id="works-cta-title">まだ形になっていない段階から、<br>ご相談ください。</h2>
  <p>会場、目的、ご予算、希望する雰囲気を伺い、編成と進行をご提案します。</p>
  <div><a class="works-showcase__button works-showcase__button--primary" href="contact.html">演奏・イベント制作を相談する</a><a class="works-showcase__button" href="achievements.html">実績一覧を見る</a></div>
</section>
</main>'''


def build() -> None:
    if DESTINATION.is_file() and "worksPerformanceGallery" in DESTINATION.read_text(encoding="utf-8"):
        raise RuntimeError(
                "Refusing to overwrite the curated 32-photo Works gallery. "
            "Update this builder's SHOWCASE and gallery data before rebuilding."
        )
    source = SOURCE.read_text(encoding="utf-8")
    stylesheet = '<link href="css/works_showcase.css" rel="stylesheet">'
    if stylesheet not in source:
        source = source.replace(
            '<link href="css/style.css" rel="stylesheet">',
            '<link href="css/style.css" rel="stylesheet">\n' + stylesheet,
            1,
        )

    preload = '<link rel="preload" as="image" href="images/works/hero-corporate-show-clean.webp" type="image/webp" fetchpriority="high">'
    if preload not in source:
        source = source.replace(stylesheet, stylesheet + "\n" + preload, 1)

    banner_start = source.index('<div id="banner1">')
    main_start = source.index("<main>")
    banner_markup = source[banner_start:main_start]
    conditional_banner = (
        "<?php if (!$seoIsRoot): ?>\n"
        + banner_markup.rstrip()
        + "\n<?php endif; ?>\n\n"
    )
    source = source[:banner_start] + conditional_banner + source[main_start:]

    main_start = source.index("<main>")
    main_end = source.index("</main>", main_start) + len("</main>")
    legacy_main = source[main_start:main_end]
    conditional_main = (
        "<?php if ($seoIsRoot): ?>\n"
        + SHOWCASE
        + "\n<?php else: ?>\n"
        + legacy_main
        + "\n<?php endif; ?>"
    )
    source = source[:main_start] + conditional_main + source[main_end:]

    modal_start = source.index("<!-- 大サイズ用モーダル -->")
    footer_start = source.index("<footer>", modal_start)
    modal_markup = source[modal_start:footer_start]
    source = (
        source[:modal_start]
        + "<?php if (!$seoIsRoot): ?>\n"
        + modal_markup
        + "<?php endif; ?>\n\n"
        + source[footer_start:]
    )
    source = source.replace('alt="株式会社MUSICIAN"', 'alt="MUSICIAN"')

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(source, encoding="utf-8", newline="\n")
    print(f"Built {DESTINATION.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
