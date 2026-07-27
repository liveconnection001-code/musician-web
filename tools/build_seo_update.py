from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "backup_2026-07-25" / "site_files"
CURRENT_COMPANY = (
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
OUTPUT = ROOT / "new_site" / "seo_deployment"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(relative_path: str, text: str) -> None:
    destination = OUTPUT / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def replace_regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    # The replacement is substituted literally (via a callback) rather than passed
    # to re.subn as a template string, because several replacement blocks contain
    # PHP regex literals (e.g. '/\s+/u') whose backslash sequences are not valid
    # re.sub group-reference escapes and would otherwise raise "bad escape".
    updated, count = re.subn(pattern, lambda _match: replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{label}: expected one regex match, found {count}")
    return updated


def replace_heading_level(
    text: str,
    old_level: int,
    new_level: int,
    class_prefix: str,
    expected: int,
    label: str,
) -> str:
    pattern = re.compile(
        rf'<h{old_level}(?P<attrs>[^>]*\bclass="{re.escape(class_prefix)}[^"]*"[^>]*)>'
        rf'(?P<body>.*?)</h{old_level}>',
        re.DOTALL,
    )
    updated, count = pattern.subn(
        lambda match: (
            f'<h{new_level}{match.group("attrs")}>'
            f'{match.group("body")}</h{new_level}>'
        ),
        text,
    )
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} matches, found {count}")
    return updated


def replace_php_preamble(text: str, preamble: str, label: str) -> str:
    return replace_regex_once(text, r"\A<\?php.*?\?>", preamble.strip(), label)


def replace_legacy_meta(text: str, replacement: str, label: str) -> str:
    # [^\r\n]* (not [^>]*) because some legacy meta blocks contain a literal '?>'
    # or other '>' inside the attribute value, which would otherwise truncate the
    # match before reaching the real end of the tag.
    pattern = (
        r"<title>[^\r\n]*</title>\s*"
        r'<meta name="description"[^\r\n]*>\s*'
        r'<meta name="keywords"[^\r\n]*>'
    )
    return replace_regex_once(text, pattern, replacement.strip(), label)


HEADER_LOGO_OLD = (
    '<h1 class="osu3"><a href="index.html"><img src="images/head_logo_1.png" '
    'alt="プロ演奏家の出張演奏サービスはMUSICIAN。" class="img-fluid"></a></h1>'
)
HEADER_LOGO_NEW = (
    '<div class="site-logo osu3"><a href="/"><img src="images/head_logo_1.png" '
    'alt="出張演奏・演奏家派遣のMUSICIAN" class="img-fluid" width="478" height="138"></a></div>'
)


def improve_shared_markup(text: str, *, banner_label: str | None = None) -> str:
    if HEADER_LOGO_OLD not in text:
        raise RuntimeError("header logo markup was not found")
    text = text.replace(HEADER_LOGO_OLD, HEADER_LOGO_NEW, 1)
    text = text.replace('href="index.html"', 'href="/"')
    text = text.replace('target="_blank"', 'target="_blank" rel="noopener noreferrer"')
    text = text.replace('alt="株式会社MUSICIAN"', 'alt="MUSICIAN"')
    text = text.replace('>株式会社MUSICIAN</a>', '>MUSICIAN</a>')
    text = text.replace(
        'https://instagram.com/musician_inc?igshid=YmMyMTA2M2Y=',
        'https://www.instagram.com/musician_office_/',
    )
    text = text.replace(
        '<p class="mb10_sp">東京都千代田区二番町9番3号</p>',
        '<p class="mb10_sp">〒102-0084　東京都千代田区二番町9番3号</p>',
    )
    text = text.replace('2022 MUSICIAN.CO.JP', '2022–2026 MUSICIAN.CO.JP')
    if banner_label:
        old = f'<h2 data-aos="fade-up">{banner_label}</h2>'
        new = f'<h1 data-aos="fade-up">{banner_label}</h1>'
        text = replace_once(text, old, new, f"banner H1 {banner_label}")
    return text


SEO_ELEMENT = r'''<?php
$seoBaseUrl = 'https://www.musician.co.jp';
$seoTitle = isset($seoTitle) ? trim($seoTitle) : 'MUSICIAN';
$seoDescription = isset($seoDescription) ? trim($seoDescription) : '';
$seoCanonicalPath = isset($seoCanonicalPath) ? trim($seoCanonicalPath) : '/';
$seoPageType = isset($seoPageType) ? $seoPageType : 'WebPage';
$seoOgType = isset($seoOgType) ? $seoOgType : 'website';
$seoImage = !empty($seoImage) ? trim($seoImage) : '/images/mv/mv_img01.jpg';
$seoBreadcrumbItems = isset($seoBreadcrumbItems) ? $seoBreadcrumbItems : array();
$seoAdditionalSchema = isset($seoAdditionalSchema) ? $seoAdditionalSchema : array();

if (preg_match('#^https?://#i', $seoCanonicalPath)) {
  $seoCanonicalUrl = $seoCanonicalPath;
} else {
  $seoCanonicalUrl = $seoBaseUrl . '/' . ltrim($seoCanonicalPath, '/');
}
if (preg_match('#^https?://#i', $seoImage)) {
  $seoImageUrl = $seoImage;
} else {
  $seoImageUrl = $seoBaseUrl . '/' . ltrim($seoImage, '/');
}

$seoEscape = function ($value) {
  return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
};

$seoOrganization = array(
  '@type' => 'Organization',
  '@id' => $seoBaseUrl . '/#organization',
  'name' => '株式会社東京アーティスト協会',
  'alternateName' => 'MUSICIAN',
  'url' => $seoBaseUrl . '/',
  'logo' => array(
    '@type' => 'ImageObject',
    'url' => $seoBaseUrl . '/images/head_logo_1.png',
    'width' => 478,
    'height' => 138
  ),
  'telephone' => '+81-3-6261-4348',
  'contactPoint' => array(
    '@type' => 'ContactPoint',
    'telephone' => '+81-3-6261-4348',
    'contactType' => 'sales',
    'availableLanguage' => array('ja')
  ),
  'sameAs' => array(
    'https://www.facebook.com/MUSICIANoffice/',
    'https://www.instagram.com/musician_office_/',
    'https://www.youtube.com/user/MUSICIANCOMPANY'
  )
);
$seoWebsite = array(
  '@type' => 'WebSite',
  '@id' => $seoBaseUrl . '/#website',
  'url' => $seoBaseUrl . '/',
  'name' => 'MUSICIAN',
  'inLanguage' => 'ja-JP',
  'publisher' => array('@id' => $seoBaseUrl . '/#organization')
);
$seoWebPage = array(
  '@type' => $seoPageType,
  '@id' => $seoCanonicalUrl . '#webpage',
  'url' => $seoCanonicalUrl,
  'name' => $seoTitle,
  'description' => $seoDescription,
  'inLanguage' => 'ja-JP',
  'isPartOf' => array('@id' => $seoBaseUrl . '/#website'),
  'about' => array('@id' => $seoBaseUrl . '/#organization'),
  'primaryImageOfPage' => array(
    '@type' => 'ImageObject',
    'url' => $seoImageUrl
  )
);

$seoGraph = array($seoOrganization, $seoWebsite, $seoWebPage);
if (!empty($seoBreadcrumbItems)) {
  $seoItemList = array();
  $seoPosition = 1;
  foreach ($seoBreadcrumbItems as $seoBreadcrumbItem) {
    $seoItemPath = isset($seoBreadcrumbItem['item']) ? $seoBreadcrumbItem['item'] : '/';
    if (!preg_match('#^https?://#i', $seoItemPath)) {
      $seoItemPath = $seoBaseUrl . '/' . ltrim($seoItemPath, '/');
    }
    $seoItemList[] = array(
      '@type' => 'ListItem',
      'position' => $seoPosition,
      'name' => $seoBreadcrumbItem['name'],
      'item' => $seoItemPath
    );
    $seoPosition++;
  }
  $seoGraph[] = array(
    '@type' => 'BreadcrumbList',
    '@id' => $seoCanonicalUrl . '#breadcrumb',
    'itemListElement' => $seoItemList
  );
}
foreach ($seoAdditionalSchema as $seoSchemaNode) {
  $seoGraph[] = $seoSchemaNode;
}
$seoJson = json_encode(
  array('@context' => 'https://schema.org', '@graph' => $seoGraph),
  JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT
);
?>
<title><?php echo $seoEscape($seoTitle); ?></title>
<meta name="description" content="<?php echo $seoEscape($seoDescription); ?>">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<link rel="canonical" href="<?php echo $seoEscape($seoCanonicalUrl); ?>">
<meta property="og:locale" content="ja_JP">
<meta property="og:type" content="<?php echo $seoEscape($seoOgType); ?>">
<meta property="og:site_name" content="MUSICIAN">
<meta property="og:title" content="<?php echo $seoEscape($seoTitle); ?>">
<meta property="og:description" content="<?php echo $seoEscape($seoDescription); ?>">
<meta property="og:url" content="<?php echo $seoEscape($seoCanonicalUrl); ?>">
<meta property="og:image" content="<?php echo $seoEscape($seoImageUrl); ?>">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="<?php echo $seoEscape($seoTitle); ?>">
<meta name="twitter:description" content="<?php echo $seoEscape($seoDescription); ?>">
<meta name="twitter:image" content="<?php echo $seoEscape($seoImageUrl); ?>">
<script type="application/ld+json"><?php echo $seoJson; ?></script>
'''


HOME_META = r'''<?php echo $this->element('seo_meta', array(
  'seoTitle' => '出張演奏・演奏家派遣ならMUSICIAN｜企業・式典・ホテル・学校公演',
  'seoDescription' => '企業パーティー、表彰式、周年記念、ホテル・商業施設、学校・公共施設などへ、プロ演奏家を全国手配。クラシック、ジャズ、和楽器ほか、企画から演奏・音響・収録までご相談いただけます。',
  'seoCanonicalPath' => '/',
  'seoPageType' => 'WebPage',
  'seoAdditionalSchema' => array(
    array(
      '@type' => 'Service',
      '@id' => 'https://www.musician.co.jp/#performance-service',
      'name' => '出張演奏・演奏家派遣サービス',
      'serviceType' => array('出張演奏', '演奏家派遣', 'イベント音楽制作'),
      'areaServed' => array('@type' => 'Country', 'name' => '日本'),
      'provider' => array('@id' => 'https://www.musician.co.jp/#organization')
    )
  )
)); ?>'''

BUSINESS_META = r'''<?php echo $this->element('seo_meta', array(
  'seoTitle' => '出張演奏・イベント音楽制作の事業案内｜MUSICIAN',
  'seoDescription' => '企業イベントや式典、ホテル、商業施設、学校・公共施設への出張生演奏を中心に、コンサート制作、楽曲制作、アーティスト手配、音響、収録・配信まで目的に合わせてご提案します。',
  'seoCanonicalPath' => '/business.html',
  'seoPageType' => 'WebPage',
  'seoBreadcrumbItems' => array(
    array('name' => 'ホーム', 'item' => '/'),
    array('name' => '事業内容', 'item' => '/business.html')
  ),
  'seoAdditionalSchema' => array(
    array(
      '@type' => 'Service',
      '@id' => 'https://www.musician.co.jp/business.html#service',
      'name' => '出張演奏・イベント音楽制作',
      'serviceType' => array('出張生演奏', 'コンサート制作・運営', '楽曲制作', 'アーティスト手配', '音響・収録・配信'),
      'areaServed' => array('@type' => 'Country', 'name' => '日本'),
      'provider' => array('@id' => 'https://www.musician.co.jp/#organization')
    )
  )
)); ?>'''

CONTACT_META = r'''<?php echo $this->element('seo_meta', array(
  'seoTitle' => '演奏依頼・出演相談・お見積り｜MUSICIAN',
  'seoDescription' => '出張演奏、演奏家・アーティストの手配、企業イベントや式典の音楽演出、コンサート制作、収録・配信のお問い合わせ・お見積りはこちら。日時や会場が未確定の段階でもご相談いただけます。',
  'seoCanonicalPath' => '/contact.html',
  'seoPageType' => 'ContactPage',
  'seoBreadcrumbItems' => array(
    array('name' => 'ホーム', 'item' => '/'),
    array('name' => 'お問い合わせ', 'item' => '/contact.html')
  )
)); ?>'''

WORKS_PREAMBLE = r'''<?php
$seoIsRoot = ((int)$target_id === 22);
$seoCategoryTitle = !empty($target['title']) ? trim(strip_tags($target['title'])) : '実施例';
$seoTitle = $seoIsRoot
  ? '出張演奏・イベント演奏の実施例｜企業式典・ホテル・配信｜MUSICIAN'
  : $seoCategoryTitle . 'の出張演奏・イベント実施例｜MUSICIAN';
$seoDescription = !empty($target['description'])
  ? trim(strip_tags($target['description']))
  : ($seoIsRoot
    ? '企業の表彰式・国際レセプション・ホテル宴会場・大規模展示会・ライブ配信まで、MUSICIANが企画から本番まで担当した出張演奏・イベント音楽制作の実施例をご紹介します。'
    : $seoCategoryTitle . 'でMUSICIANが担当した出張演奏やイベント音楽制作の実施例をご紹介します。');
$seoCanonicalPath = $seoIsRoot ? '/works.html' : '/works/index/' . (int)$target_id;
$seoImage = $seoIsRoot ? '/images/works/hero-corporate-show-clean.jpg' : '/images/mv/mv_img01.jpg';
$seoBreadcrumbItems = array(
  array('name' => 'ホーム', 'item' => '/'),
  array('name' => '実施例', 'item' => '/works.html')
);
if (!$seoIsRoot) {
  $seoBreadcrumbItems[] = array('name' => $seoCategoryTitle, 'item' => $seoCanonicalPath);
}
?>'''

COMPANY_PREAMBLE = r'''<?php
$seoIsRoot = ((int)$target_id === 21);
$seoCategoryTitle = !empty($target['title']) ? trim(strip_tags($target['title'])) : 'MUSICIANについて';
$seoTitle = $seoIsRoot
  ? 'MUSICIANについて・演奏実績｜出張演奏・演奏家派遣'
  : $seoCategoryTitle . 'の演奏・イベント実績｜MUSICIAN';
$seoDescription = !empty($target['description'])
  ? trim(strip_tags($target['description']))
  : ($seoIsRoot
    ? '出張演奏・演奏家派遣のMUSICIANについて、サービス方針と2010年から2026年までの主な企業イベント、式典、ホテル、商業施設、学校公演などの実績をご紹介します。'
    : $seoCategoryTitle . 'にMUSICIANが担当した主な出張演奏、企業イベント、式典、ホテル・商業施設などの実績をご紹介します。');
$seoCanonicalPath = $seoIsRoot ? '/company.html' : '/company/index/' . (int)$target_id;
$seoBreadcrumbItems = array(
  array('name' => 'ホーム', 'item' => '/'),
  array('name' => 'MUSICIANについて', 'item' => '/company.html')
);
if (!$seoIsRoot) {
  $seoBreadcrumbItems[] = array('name' => $seoCategoryTitle, 'item' => $seoCanonicalPath);
}
?>'''

ARTIST_INDEX_PREAMBLE = r'''<?php
$seoTitle = 'プロ演奏家・アーティスト一覧｜MUSICIAN';
$seoDescription = 'クラシック、ジャズ、和楽器、民族楽器ほか、MUSICIANが演奏スキルを確認したプロ演奏家・アーティストをご紹介します。企業イベント、式典、ホテル、学校公演などの出演依頼をご相談いただけます。';
$seoCanonicalPath = '/artist.html';
$seoBreadcrumbItems = array(
  array('name' => 'ホーム', 'item' => '/'),
  array('name' => 'アーティスト', 'item' => '/artist.html')
);
?>'''

ARTIST_VIEW_PREAMBLE = r'''<?php
// viewには該当するアーティスト情報が保持されているため、先に展開します。
extract($box['CatalogBox'], EXTR_PREFIX_ALL, 'tbl');
extract($category['CatalogCategory'], EXTR_PREFIX_ALL, 'category');

$seoArtistTitle = trim(strip_tags($tbl_title));
$seoProfileText = !empty($tbl_html1) ? html_entity_decode(strip_tags($tbl_html1), ENT_QUOTES, 'UTF-8') : '';
$seoProfileText = trim(preg_replace('/\s+/u', ' ', $seoProfileText));
if (!empty($box['CatalogBox']['description'])) {
  $seoDescription = trim(strip_tags($box['CatalogBox']['description']));
} elseif (!empty($seoProfileText)) {
  $seoExcerpt = function_exists('mb_substr') ? mb_substr($seoProfileText, 0, 115, 'UTF-8') : substr($seoProfileText, 0, 115);
  $seoDescription = $seoArtistTitle . 'のプロフィール。' . $seoExcerpt;
} else {
  $seoDescription = $seoArtistTitle . 'のプロフィールと演奏情報。企業イベント、式典、ホテル、学校公演などの出演依頼はMUSICIANへご相談ください。';
}
$seoTitle = $seoArtistTitle . '｜演奏依頼・プロフィール｜MUSICIAN';
$seoCanonicalPath = '/artist/view/' . (int)$tbl_id;
$seoImage = !empty($tbl_image1)
  ? $this->element('media', array('var' => array('id' => $tbl_image1, 'width' => 1200, 'return' => true)))
  : '/images/mv/mv_img01.jpg';
$seoBreadcrumbItems = array(
  array('name' => 'ホーム', 'item' => '/'),
  array('name' => 'アーティスト', 'item' => '/artist.html'),
  array('name' => $seoArtistTitle, 'item' => $seoCanonicalPath)
);
?>'''

DYNAMIC_META = r'''<?php echo $this->element('seo_meta', array(
  'seoTitle' => $seoTitle,
  'seoDescription' => $seoDescription,
  'seoCanonicalPath' => $seoCanonicalPath,
  'seoPageType' => 'CollectionPage',
  'seoBreadcrumbItems' => $seoBreadcrumbItems
)); ?>'''

ARTIST_VIEW_META = r'''<?php echo $this->element('seo_meta', array(
  'seoTitle' => $seoTitle,
  'seoDescription' => $seoDescription,
  'seoCanonicalPath' => $seoCanonicalPath,
  'seoPageType' => 'ProfilePage',
  'seoImage' => $seoImage,
  'seoBreadcrumbItems' => $seoBreadcrumbItems
)); ?>'''


HOME_WORKS_SECTION = r'''<section class="pd_yohaku_r home-works" aria-labelledby="home-works-title">
  <h2 id="home-works-title" class="midashi1 mb30_md50 tal_sptac"><span class="en">Works</span>実施例</h2>
  <p class="home-works__lead">MUSICIANが企画から本番まで担当した仕事を、6つのテーマからご紹介します。</p>
  <div class="top_works clearfix" role="list" aria-label="主な仕事例">
    <div class="box" role="listitem"><a href="works.html#work-corporate-event"><div class="image"><span class="photo-ofi"><picture><source srcset="images/works/corporate-party-clean.webp" type="image/webp"><img src="images/works/corporate-party-clean.jpg" alt="企業パーティーのステージに並ぶ6名編成の女性バンド" class="img-fluid" width="1440" height="900" loading="lazy" decoding="async"></picture></span></div><div class="text">表彰式の余韻を、6名編成のライブショーへ</div></a></div>
    <div class="box" role="listitem"><a href="works.html#work-international-reception"><div class="image"><span class="photo-ofi"><picture><source srcset="images/works/international-reception-clean.webp" type="image/webp"><img src="images/works/international-reception-clean.jpg" alt="国際レセプション会場で演奏するヴァイオリンとチェロのデュオ" class="img-fluid" width="1440" height="900" loading="lazy" decoding="async"></picture></span></div><div class="text">ゲストに上質な響きを</div></a></div>
    <div class="box" role="listitem"><a href="works.html#work-japanese-culture"><div class="image"><span class="photo-ofi"><picture><source srcset="images/works/japanese-hospitality-clean.webp" type="image/webp"><img src="images/works/japanese-hospitality-clean.jpg" alt="国際会議の歓迎演出で和楽器を演奏するステージ" class="img-fluid" width="1440" height="900" loading="lazy" decoding="async"></picture></span></div><div class="text">和のお出迎え</div></a></div>
    <div class="box" role="listitem"><a href="works.html#work-hotel-party"><div class="image"><span class="photo-ofi"><picture><source srcset="images/works/hotel-live-clean.webp" type="image/webp"><img src="images/works/hotel-live-clean.jpg" alt="ホテル宴会場で演奏するジャズカルテット" class="img-fluid" width="1440" height="900" loading="lazy" decoding="async"></picture></span></div><div class="text">宴会場をライブステージへ</div></a></div>
    <div class="box" role="listitem"><a href="works.html#work-large-venue"><div class="image"><span class="photo-ofi"><picture><source srcset="images/works/large-event-clean.webp" type="image/webp"><img src="images/works/large-event-clean.jpg" alt="多くの来場者が集まる大規模展示会のステージ" class="img-fluid" width="1440" height="900" loading="lazy" decoding="async"></picture></span></div><div class="text">展示会を支える</div></a></div>
    <div class="box" role="listitem"><a href="works.html#work-live-streaming"><div class="image"><span class="photo-ofi"><picture><source srcset="images/works/live-streaming-clean.webp" type="image/webp"><img src="images/works/live-streaming-clean.jpg" alt="ライブ配信現場の映像と音声のオペレーション卓" class="img-fluid" width="1440" height="900" loading="lazy" decoding="async"></picture></span></div><div class="text">臨場感を演出</div></a></div>
  </div>
  <p class="tar_sptac"><a href="works.html" class="btn btn-1">実施例を見る</a></p>
</section>'''


def build_home() -> None:
    text = read(BACKUP / "app" / "View" / "Homes" / "index.html")
    text = replace_legacy_meta(text, HOME_META, "home metadata")
    text = improve_shared_markup(text)
    text = replace_regex_once(
        text,
        r'<section class="pd_yohaku_r">\s*<h3 class="midashi1 mb30_md50 tal_sptac"><span class="en">Works</span>実施例</h3>.*?</section>',
        HOME_WORKS_SECTION,
        "home curated Works section",
    )
    text = replace_heading_level(text, 3, 2, "midashi1", 4, "home section headings")
    text = replace_once(
        text,
        '<h2 class="ja caption mb40">大切な瞬間を彩る、華やかな生演奏</h2>',
        '<h1 class="ja caption mb40">大切な瞬間を彩る、華やかな生演奏</h1>',
        "home H1",
    )
    text = replace_once(
        text,
        "\t\t\t\tオールジャンルのアーティストより、<br>\n"
        "\t\t\t\tイベント制作経験豊富な当社が<br class=\"d-md-none\">最高のプランをご提案させて頂きます。<br>\n"
        "\t\t\t\tどうぞお気軽にご相談下さい。",
        "\t\t\t\t企業パーティー、表彰式、周年行事、ホテル・商業施設、学校公演などへ、<br>\n"
        "\t\t\t\tイベント制作経験豊富なスタッフが目的に合うプロ演奏家と演出をご提案します。<br>\n"
        "\t\t\t\t<a href=\"works.html\">演奏実績</a>・<a href=\"artist.html\">アーティスト</a>をご覧のうえ、<a href=\"contact.html\">お気軽にご相談ください</a>。",
        "home audience copy",
    )
    text = replace_once(
        text,
        '<img class="object-fit-img cover" src="images/mv/mv_img01.jpg" alt="">',
        '<img class="object-fit-img cover" src="images/mv/mv_img01.jpg" alt="企業イベントを彩るプロ演奏家の生演奏" fetchpriority="high" decoding="async">',
        "home LCP image",
    )
    text = text.replace(
        'class="object-fit-img cover"',
        'class="object-fit-img cover" loading="lazy" decoding="async"',
    )
    text = text.replace(
        'class="img-fluid"></span>',
        'class="img-fluid" loading="lazy" decoding="async"></span>',
    )
    youtube_titles = {
        "Q3I7bU3JHng": "MUSICIAN 出張演奏・イベント映像 1",
        "Yqte27z2aww": "MUSICIAN 出張演奏・イベント映像 2",
        "-w4a-s-tlgo": "MUSICIAN 出張演奏・イベント映像 3",
    }
    for video_id, title in youtube_titles.items():
        text = text.replace(
            f'src="https://www.youtube.com/embed/{video_id}" title="YouTube video player"',
            f'src="https://www.youtube.com/embed/{video_id}" title="{title}" loading="lazy"',
        )
    write("app/View/Homes/index.html", text)


def build_static_pages() -> None:
    business = read(BACKUP / "app" / "webroot" / "business.html")
    business = replace_legacy_meta(business, BUSINESS_META, "business metadata")
    business = improve_shared_markup(business, banner_label="<span>Business</span>事業内容")
    business = replace_heading_level(business, 3, 2, "midashi2", 6, "business section headings")
    for image_number in ("01", "02", "04", "05"):
        business = business.replace(
            f'src="images/business_photo{image_number}.jpg"',
            f'src="images/business_photo{image_number}.jpg" loading="lazy" decoding="async"',
        )
    write("app/webroot/business.html", business)

    contact = read(BACKUP / "app" / "webroot" / "contact.html")
    contact = replace_legacy_meta(contact, CONTACT_META, "contact metadata")
    contact = improve_shared_markup(contact, banner_label="<span>Contact</span>お問い合わせ")
    contact = replace_heading_level(contact, 3, 2, "midashi1", 1, "contact form heading")
    contact = replace_heading_level(contact, 3, 2, "midashi4", 1, "privacy policy heading")
    contact = replace_heading_level(contact, 4, 3, "midashi5", 4, "privacy policy subheadings")
    contact = contact.replace(' enctype="multipart/form-data"', '')
    contact = replace_once(
        contact,
        'アーティストのブッキング、各種お問い合わせは<br class="d-none d-sm-block">こちらのメールフォームまたはお電話でご連絡ください。',
        '出張演奏、演奏家・アーティストの手配、企業イベントや式典の音楽演出は、<br class="d-none d-sm-block">日時や会場が未確定の段階でもメールフォームまたはお電話でご相談いただけます。',
        "contact intro copy",
    )
    write("app/webroot/contact.html", contact)


def build_catalog_pages() -> None:
    works = read(BACKUP / "app" / "View" / "catalog" / "cl01_2" / "default" / "index.html")
    works = replace_php_preamble(works, WORKS_PREAMBLE, "works preamble")
    works = replace_legacy_meta(works, DYNAMIC_META, "works metadata")
    works = works.replace(
        "  'seoCanonicalPath' => $seoCanonicalPath,\n",
        "  'seoCanonicalPath' => $seoCanonicalPath,\n  'seoImage' => $seoImage,\n",
        1,
    )
    works = improve_shared_markup(works, banner_label="<span>Works</span>実施例")
    works = replace_heading_level(works, 3, 2, "midashi3", 1, "works category heading")
    works = replace_heading_level(works, 4, 3, "midashi2", 1, "works item heading")
    works = works.replace(
        'class="img-fluid"></span>',
        'class="img-fluid" loading="lazy" decoding="async"></span>',
    )
    write("app/View/catalog/cl01_2/default/index.html", works)

    company = read(CURRENT_COMPANY)
    company = replace_php_preamble(company, COMPANY_PREAMBLE, "company preamble")
    company = replace_legacy_meta(company, DYNAMIC_META, "company metadata")
    company = improve_shared_markup(company, banner_label="<span>About us</span>私たちについて")
    company = replace_heading_level(company, 3, 2, "midashi1", 5, "company section headings")
    company = replace_heading_level(company, 4, 3, "recent-achievements__title", 1, "recent achievements heading")
    company = replace_heading_level(company, 4, 3, "midashi3", 1, "company category heading")
    company = replace_once(company, "<h4>2018年以前の実績</h4>", "<h3>2018年以前の実績</h3>", "archive achievements heading")
    company = replace_once(
        company,
        '<p class="pankuzu"><a href="/">Home</a>&nbsp;&nbsp;&gt;&nbsp;&nbsp;Company</p>',
        '<p class="pankuzu"><a href="/">Home</a>&nbsp;&nbsp;&gt;&nbsp;&nbsp;<a href="company.html">MUSICIANについて</a><?php if (!$seoIsRoot): ?>&nbsp;&nbsp;&gt;&nbsp;&nbsp;<?php echo h($seoCategoryTitle); ?><?php endif; ?></p>',
        "company visible breadcrumb",
    )
    company = replace_once(
        company,
        """					<tr>
					  <th>名称</th>
					  <td>MUSICIAN</td>
					</tr>""",
        """					<tr>
					  <th>会社名</th>
					  <td>株式会社東京アーティスト協会</td>
					</tr>
					<tr>
					  <th>ブランド名</th>
					  <td>MUSICIAN</td>
					</tr>""",
        "company legal and brand names",
    )
    company = company.replace(
        'class="img-fluid"></span>',
        'class="img-fluid" loading="lazy" decoding="async"></span>',
    )
    write("app/View/catalog/cl01_3/default/index.html", company)

    artist_index = read(BACKUP / "app" / "View" / "catalog" / "cl02_4" / "default" / "index.html")
    artist_index = replace_php_preamble(artist_index, ARTIST_INDEX_PREAMBLE, "artist index preamble")
    artist_index = replace_legacy_meta(artist_index, DYNAMIC_META, "artist index metadata")
    artist_index = improve_shared_markup(artist_index, banner_label="<span>Artist</span>アーティスト")
    artist_index = replace_heading_level(artist_index, 3, 2, "midashi2", 1, "artist index heading")
    artist_index = artist_index.replace(
        'class="img-fluid"></span>',
        'class="img-fluid" loading="lazy" decoding="async"></span>',
    )
    write("app/View/catalog/cl02_4/default/index.html", artist_index)

    artist_view = read(BACKUP / "app" / "View" / "catalog" / "cl02_4" / "default" / "view.html")
    artist_view = replace_php_preamble(artist_view, ARTIST_VIEW_PREAMBLE, "artist view preamble")
    artist_view = replace_legacy_meta(artist_view, ARTIST_VIEW_META, "artist view metadata")
    artist_view = improve_shared_markup(artist_view, banner_label="<span>Artist</span>アーティスト")
    artist_view = replace_heading_level(artist_view, 3, 2, "midashi2", 1, "artist category heading")
    artist_view = artist_view.replace(
        'class="img-fluid"></div>',
        'class="img-fluid" loading="lazy" decoding="async"></div>',
    )
    write("app/View/catalog/cl02_4/default/view.html", artist_view)


def build_contact_results() -> None:
    pages = {
        "msg.html": (
            "お問い合わせ内容の確認｜MUSICIAN",
            "お問い合わせ内容の確認画面です。",
        ),
        "thanks.html": (
            "お問い合わせ送信完了｜MUSICIAN",
            "お問い合わせを受け付けました。",
        ),
    }
    for filename, (title, description) in pages.items():
        text = read(BACKUP / "app" / "View" / "Contact" / filename)
        meta = (
            f"<title>{title}</title>\n"
            f'<meta name="description" content="{description}">\n'
            '<meta name="robots" content="noindex, nofollow">\n'
            '<link rel="canonical" href="https://www.musician.co.jp/contact.html">'
        )
        text = replace_legacy_meta(text, meta, f"{filename} noindex metadata")
        text = improve_shared_markup(text, banner_label="<span>Contact</span>お問い合わせ")
        text = replace_heading_level(text, 3, 2, "midashi1", 1, f"{filename} form heading")
        write(f"app/View/Contact/{filename}", text)


def build_css() -> None:
    css = read(BACKUP / "app" / "webroot" / "css" / "style.css")
    css = replace_once(css, "h1 {float: left;}", ".site-logo {float: left;}", "site logo float")
    css = css.replace("h1 img{", ".site-logo img{")
    css = css.replace(".cb-header h1 img{", ".cb-header .site-logo img{")
    css = css.replace("#midashi_h2 h2", "#midashi_h2 h1")
    css += """

/* SEO 2026-07: meaningful inline links in the main visual */
.sub_caption a { color: inherit; text-decoration: underline; text-underline-offset: 0.2em; }
.sub_caption a:hover, .sub_caption a:focus { text-decoration-thickness: 2px; }

/* Curated homepage Works: same approved clean assets and themes as /works.html */
.home-works__lead { line-height: 1.9; margin: -10px 0 32px; }
.home-works .box a { display: block; }
.home-works .box .image { background: #041e42; overflow: hidden; }
.home-works .box img { transition: transform .45s ease; width: 100%; }
.home-works .box a:hover img, .home-works .box a:focus-visible img { transform: scale(1.018); }
.home-works .box a:focus-visible { outline: 3px solid #e36927; outline-offset: 4px; }
@media (prefers-reduced-motion: reduce) { .home-works .box img { transition: none; } }
"""
    write("app/webroot/css/style.css", css)


def build_javascript() -> None:
    bootstrap = read(BACKUP / "app" / "webroot" / "js" / "bootstrap.js")
    bootstrap = replace_once(
        bootstrap,
        "  if (typeof Tether === 'undefined') {\n    throw new Error('Bootstrap tooltips require Tether (http://tether.io/)');\n  }",
        "  // Tooltip/Popover are unused on this site; keep Modal available without failing when legacy Tether is absent.\n  if (typeof Tether === 'undefined') {\n    // Intentionally continue. A later explicit tooltip call still requires Tether.\n  }",
        "Bootstrap Tether compatibility guard",
    )
    write("app/webroot/js/bootstrap.js", bootstrap)

    title = read(BACKUP / "app" / "webroot" / "js" / "title.js")
    pattern = re.compile(
        r"var scrollElemToWatch_1 = document\.getElementById\('([^']+)'\),\s+watcher_1 ="
    )
    title, count = pattern.subn(
        lambda match: (
            f"var scrollElemToWatch_1 = document.getElementById('{match.group(1)}');\n"
            "        if (!scrollElemToWatch_1) return;\n"
            "        var watcher_1 ="
        ),
        title,
    )
    if count != 8:
        raise RuntimeError(f"title.js guard: expected 8 animation targets, found {count}")
    write("app/webroot/js/title.js", title)

def build_routing_and_errors() -> None:
    routes = read(BACKUP / "app" / "Config" / "routes.php")
    route_marker = "Router::connect('/robots.txt', array('controller' => 'homes', 'action' => 'robots'));"
    routes = replace_once(
        routes,
        route_marker,
        route_marker
        + "\n\n// 既知の静的ページ以外の .html URL はホームを返さず、正しい404応答にする\n"
        + "Router::connect('/homes/login', array('controller' => 'homes', 'action' => 'not_found'));\n"
        + "Router::connect('/homes/maintenance', array('controller' => 'homes', 'action' => 'not_found'));\n"
        + "Router::connect('/:slug.html', array('controller' => 'homes', 'action' => 'not_found'), array('slug' => '[A-Za-z0-9_-]+'));",
        "404 route",
    )
    write("app/Config/routes.php", routes)

    controller = read(BACKUP / "app" / "Controller" / "HomesController.php")
    controller = replace_once(
        controller,
        "  function maintenance() {\n  }",
        "  public function maintenance() {\n    return $this->not_found();\n  }",
        "disable legacy maintenance action",
    )
    controller = replace_regex_once(
        controller,
        r"  public function login\(\) \{.*?\n  \}",
        "  public function login() {\n    return $this->not_found();\n  }",
        "disable legacy login action",
    )
    controller = replace_regex_once(
        controller,
        r"  public function webroot\(\$file\) \{.*?\n  \}",
        r"""  public function webroot($file) {
    $this->webroot_file = $file;
    $requested = str_replace('\\', '/', (string)$file);

    if ($requested === '' || strtolower(pathinfo($requested, PATHINFO_EXTENSION)) !== 'html' || strpos($requested, chr(0)) !== false || preg_match('#(^|/)\.\.(/|$)#', $requested)) {
      return $this->not_found();
    }

    $root = realpath(WWW_ROOT);
    $resolved = realpath(WWW_ROOT . str_replace('/', DS, ltrim($requested, '/')));
    if ($root === false || $resolved === false || !is_file($resolved) || strpos($resolved, $root . DS) !== 0) {
      return $this->not_found();
    }

    $this->set('file', $resolved);
  }""",
        "harden legacy webroot action",
    )
    controller = replace_once(
        controller,
        "  public function robots() {\n    $this->layout = \"ajax\";\n    $this->response->type(\"text/plain\");\n  }",
        "  public function not_found() {\n"
        "    $this->layout = false;\n"
        "    $this->response->statusCode(404);\n"
        "    $this->response->type('html');\n"
        "    $this->render('/Errors/error400');\n"
        "  }\n\n"
        "  public function robots() {\n"
        "    $this->layout = \"ajax\";\n"
        "    $this->response->type(\"text/plain\");\n"
        "  }",
        "404 controller action",
    )
    write("app/Controller/HomesController.php", controller)

    error400 = r'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ページが見つかりません｜MUSICIAN</title>
  <meta name="description" content="お探しのページは移動または削除された可能性があります。">
  <meta name="robots" content="noindex, follow">
  <style>
    body { margin: 0; background: #f7f4ef; color: #272329; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Yu Gothic", sans-serif; }
    main { max-width: 720px; margin: 0 auto; padding: 10vh 24px; text-align: center; }
    img { width: min(300px, 80vw); height: auto; }
    h1 { margin: 56px 0 20px; font-size: clamp(1.6rem, 4vw, 2.4rem); }
    p { line-height: 1.9; }
    nav { margin-top: 36px; display: flex; flex-wrap: wrap; justify-content: center; gap: 12px 22px; }
    a { color: #53372f; text-underline-offset: 0.2em; }
  </style>
</head>
<body>
  <main>
    <a href="/"><img src="/images/head_logo_1.png" width="478" height="138" alt="出張演奏・演奏家派遣のMUSICIAN"></a>
    <h1>ページが見つかりません</h1>
    <p>URLをご確認いただくか、下記のメニューからお探しください。</p>
    <nav aria-label="主要ページ">
      <a href="/">ホーム</a>
      <a href="/business.html">事業内容</a>
      <a href="/works.html">実施例</a>
      <a href="/artist.html">アーティスト</a>
      <a href="/company.html">MUSICIANについて</a>
      <a href="/contact.html">お問い合わせ</a>
    </nav>
  </main>
</body>
</html>
'''
    write("app/View/Errors/error400.html", error400)


def build_htaccess() -> None:
    root_htaccess = read(BACKUP / ".htaccess")
    marker = "  #↓adminが上手く見れない時、コメントアウトを外してみる↓"
    redirects = """  # SEO: duplicate public URLs are permanently redirected to one canonical URL
  RewriteRule ^index\\.html$ https://www.musician.co.jp/ [R=301,L]
  RewriteRule ^works/index/22(?:/page:1)?/?$ https://www.musician.co.jp/works.html [R=301,L,NE]
  RewriteRule ^company/index/21/?$ https://www.musician.co.jp/company.html [R=301,L,NE]
  RewriteRule ^works/index/(4|25)/page:1/?$ https://www.musician.co.jp/works/index/$1 [R=301,L,NE]
  RewriteRule ^company/index/(5|6|7|12|13|14|15|16|17|18|19|20)/page:1/?$ https://www.musician.co.jp/company/index/$1 [R=301,L,NE]

"""
    root_htaccess = replace_once(root_htaccess, marker, redirects + marker, "canonical redirects")
    write(".htaccess", root_htaccess)

    webroot_htaccess = read(BACKUP / "app" / "webroot" / ".htaccess")
    security_prefix = r'''Options -Indexes

<IfModule mod_headers.c>
  Header always set X-Content-Type-Options "nosniff"
  Header always set X-Frame-Options "SAMEORIGIN"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
  Header always unset X-Powered-By
</IfModule>

<FilesMatch "(^\.|\.(?:bak|old|orig|save|swp|sql|log|ini|env|ya?ml|zip|tar|gz)$)">
  <IfModule mod_authz_core.c>
    Require all denied
  </IfModule>
  <IfModule !mod_authz_core.c>
    Order allow,deny
    Deny from all
  </IfModule>
</FilesMatch>

'''
    webroot_htaccess = security_prefix + webroot_htaccess
    marker = "\t#SHOP専用ブロックここから"
    blocks = r"""    # Security: disable obsolete CMS/sample entry points and unsafe methods
    RewriteCond %{REQUEST_METHOD} ^TRACE$ [NC]
    RewriteRule .* - [R=405,L]
    RewriteRule ^(?:SampleKit|securimage|admin_sp|catalog_preview|_dl|_bk_[^/]+)(?:/|$) - [R=404,L,NC]
    RewriteRule ^ez_js/eq(?:/|$) - [R=404,L,NC]
    RewriteRule ^ez_js/pdf/web(?:/|$) - [R=404,L,NC]
    RewriteRule (?:^|/)\.(?!well-known(?:/|$)) - [F,L]

"""
    webroot_htaccess = replace_once(webroot_htaccess, marker, blocks + marker, "demo page 404 rules")
    write("app/webroot/.htaccess", webroot_htaccess)


def build_robots_and_sitemap() -> None:
    robots = r'''User-agent: *
<?php if (Configure::read('debug') > 0):?>
Disallow: /
<?php else:?>
Disallow: /admin/
Disallow: /admin_sp/
Disallow: /data_files/
Disallow: /catalog_preview/
Disallow: /_bk_20221124/
Disallow: /_dl/
Disallow: /SampleKit/
Disallow: /securimage/example_form
Disallow: /ez_js/eq/
Disallow: /ez_js/pdf/web/
Disallow: /maintenance.html
<?php endif;?>

Sitemap: https://www.musician.co.jp/sitemap.xml
'''
    write("app/View/Homes/robots.html", robots)

    urls = [
        ("/", "1.0"),
        ("/business.html", "0.9"),
        ("/works.html", "0.9"),
        ("/artist.html", "0.9"),
        ("/company.html", "0.9"),
        ("/contact.html", "0.8"),
        ("/works/index/4", "0.7"),
        ("/works/index/25", "0.7"),
    ]
    urls.extend((f"/company/index/{category_id}", "0.6") for category_id in (5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19, 20))
    artist_ids = (38, 63, 56, 55, 51, 50, 49, 46, 91, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 62, 61, 60, 59, 58, 53, 54, 57)
    urls.extend((f"/artist/view/{artist_id}", "0.6") for artist_id in artist_ids)

    rows = []
    for path, priority in urls:
        loc = "https://www.musician.co.jp/" if path == "/" else "https://www.musician.co.jp" + path
        rows.append(
            "  <url>\n"
            f"    <loc>{escape(loc)}</loc>\n"
            "    <lastmod>2026-07-26</lastmod>\n"
            "    <changefreq>monthly</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            "  </url>"
        )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )
    write("app/webroot/sitemap.xml", sitemap)


def write_manifest() -> None:
    files = []
    for path in sorted(p for p in OUTPUT.rglob("*") if p.is_file() and p.name not in {"seo_manifest.json", "CLAUDE_REVIEW.md"}):
        payload = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(OUTPUT).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest = {
        "generated_at_jst": "2026-07-26",
        "source_backup": str(BACKUP),
        "company_template_source": str(CURRENT_COMPANY),
        "production_uploaded": False,
        "file_count": len(files),
        "files": files,
    }
    write("seo_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    write("app/View/Elements/seo_meta.html", SEO_ELEMENT)
    build_home()
    build_static_pages()
    build_catalog_pages()
    build_contact_results()
    build_css()
    build_javascript()
    build_routing_and_errors()
    build_htaccess()
    build_robots_and_sitemap()
    write_manifest()
    print(f"Built SEO deployment package: {OUTPUT}")


if __name__ == "__main__":
    main()
