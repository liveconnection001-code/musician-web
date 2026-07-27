# MUSICIAN SEOアップデート 第三者レビュー(Claude)

- レビュー対象: `A:\AI\Web\MUSICIAN\new_site\seo_deployment`(および許可範囲内の `temporary_preview_site` プレビュー資産、`tools` 配下のSEO関連Pythonスクリプト)
- 実施日: 2026-07-26
- 前提: 本番サーバーへのアップロード・FTP操作は一切行っていない。SSL証明書発行待ちであり、SSL復旧を待たずローカルファイルのみを対象にレビューした。バックアップ原本(`backup_2026-07-25`)および現行本番相当ソース(`new_site/deployment`)は変更していない。

## 総合判定: 修正後に反映可能(実行系検証が未完了のため条件付き)

`new_site/seo_deployment` の19ファイルを静的に精査した限り、CakePHPテンプレート・.htaccess・SEOメタ情報・sitemap.xml・robots.txt・HTML構造・実績データ・COVID時期の文言のいずれにも**確定的な不具合は見つからなかった**。ただし、このレビュー環境には **PHP・Python・Node.jsのいずれも実行可能な形でインストールされておらず**、`php -l`・`tools/validate_seo_update.py`・プレビューサイトのビルドという、ユーザーが要求した実行系の検証を実際には実行できていない。したがって「本番反映可能」と断定はせず、「本番反映前に、実行環境(PHP/Python/Node.jsが使える環境)で以下の実行系検証を必ず完走させること」を条件とした判定とする。

## 発見した問題

### 1. (対応済み・ツール限定) `build_seo_update.py` 単体では実行に失敗する状態だった
`tools/run_build_seo_update.py` と `tools/run_build_seo_update_final.py` は、`build_seo_update.py` 本体の2つの正規表現処理をモンキーパッチで上書きしていた。
- `replace_legacy_meta` が `[^>]*` を使っており、meta属性値中に `>` (例: `?>` の埋め込み)が含まれる実ページで、タグの終端より手前で正規表現の一致が打ち切られ、後続の `<meta name="keywords">` との連続一致に失敗し `RuntimeError` になり得た。
- `replace_regex_once` が置換文字列を `re.subn` にテンプレートとしてそのまま渡していたため、プレースホルダー文字列に `\s+` (`ARTIST_VIEW_PREAMBLE` 内の `preg_replace('/\s+/u', ...)` 等)のようなPHPの正規表現リテラルが含まれる場合、Pythonの `re` モジュールが不正なエスケープ(`bad escape`)として例外を送出し得た。

これらは実際に不具合を引き起こすため2つの互換ランナーが作られていたが、**両修正とも「一致範囲を安全に広げる」「置換文字列をエスケープ解釈せず文字通り使う」という、既存の正しい一致結果には一切影響しない修正**であることをコードレベルで確認できた(狭い方のパターンで一致していた内容は、広い方のパターンでも必ず同じ内容に一致する)。よって両修正を `build_seo_update.py` 本体に統合し、重複していた2つのランナースクリプトを削除した(詳細は「実施した修正」を参照)。

**重要な限界**: この環境にはPythonの実行可能な処理系がなく(`python`/`python3`/`py` はいずれも動作しない、`C:\Users\...\WindowsApps\python.exe` のストア誘導スタブのみ)、統合後の `build_seo_update.py` を実際に実行して出力をバイト単位で再検証することはできていない。統合はコードレビューのみに基づく。**本番反映前に、Pythonが使える環境で `python tools/build_seo_update.py && python tools/finalize_seo_update.py && python tools/validate_seo_update.py` を実行し、現在 `new_site/seo_deployment` にある19ファイルと出力が一致すること(特に85件の近年実績と会社ページの内容が失われていないこと)を確認してほしい。**

### 2. (未解決・要確認) works以外のカテゴリのpage:1重複URLの扱いに一貫性がない可能性
`.htaccess` には `works/index/(4|25)/page:1` → `/works/index/$1` の恒久転送があるが、company側のサブカテゴリ(id: 5,6,7,12〜20の12件)には同種の `.../page:1` 転送ルールが存在しない。works側の2カテゴリだけに転送が用意されているのは、それらのカテゴリだけ実際にページネーションが発生する(1ページ目に収まらない件数がある)ためだと推測できるが、これはCMS側のデータ件数に依存し、本ファイル群だけでは真偽を確認できない。もしcompanyのいずれかのサブカテゴリも2ページ目以降を持つ場合、`/company/index/{id}/page:1` が正規化されないまま残る可能性がある。

このルールを推測で追加すると、company側のルート(id=21)は `/company/index/21/page:1` → `/company/index/21` → (別ルールで) `/company.html` という**2段階リダイレクト**になり、要件にある「不要なリダイレクトを経由しない」に抵触しかねないため、**確証のないまま`.htaccess`を追加修正することはしなかった**。本番相当環境で各company系カテゴリに2ページ目が実在するかを確認し、必要な場合のみ、ルートカテゴリ(21)を除外した形でworksと同様のルールを追加することを推奨する。

### 3. (確認のみ・問題なし) ルート判定ロジックの前提はコントローラ実装と整合していた
`WORKS_PREAMBLE`/`COMPANY_PREAMBLE` は `(int)$target_id === 22`/`=== 21` でトップページ相当かを判定するが、これは推測ではなく `WorksController`/`CompanyController` の `$skip_root_index = true` により `/works.html`・`/company.html` へ直接アクセスした場合に `$target_id` が「並び順で最初のカテゴリID」に自動解決される実装と整合していることを、両コントローラのソース(`app/Controller/WorksController.php` 340行目付近、`CompanyController.php` 同様)を読んで確認した。`ArtistController` は `$skip_root_index = false` であり、`ARTIST_INDEX_PREAMBLE` がルート判定ロジックを持たないことも整合している。id=21/22が実データ上も「最初に並ぶカテゴリ」であることの最終確認は本番DBでのみ可能。

## 実施した修正

1. **`tools/build_seo_update.py`**: `replace_legacy_meta` の正規表現を `[^>]*` → `[^\r\n]*`(title/description/keywordsの3箇所)に、`replace_regex_once` を置換文字列をコールバック経由でリテラルに適用する方式に変更。これにより本スクリプト単体で(旧ランナー不要で)正しく動作するようにした。中身の置換ロジック・生成される文字列は一切変更していない。
2. **`tools/run_build_seo_update.py`**: 削除(修正1により不要化。他ファイルからの参照が無いことを`grep`で確認済み)。
3. **`tools/run_build_seo_update_final.py`**: 削除(同上)。
4. **`tools/__pycache__/run_build_seo_update*.cpython-312.pyc`**: 削除(上記2ファイルの古いバイトコードキャッシュ)。
5. **`new_site/seo_deployment/README.md`**: ビルド手順を「`build_seo_update.py` → `finalize_seo_update.py` → `validate_seo_update.py`」の単一パイプラインとして明記し、旧ランナー削除の経緯を追記。
6. **`new_site/seo_deployment/CLAUDE_REVIEW.md`**: 本ファイルを新規作成。

`new_site/seo_deployment` 配下のHTML/PHP/.htaccess/sitemap.xml/robots.html等の**生成済みコンテンツ自体には変更を加えていない**(静的検証の結果、要求仕様を満たしていることを確認できたため)。

## 未解決事項

- **PHP未インストール**: このレビュー環境に `php` コマンドが無く(`php -v` は `command not found`)、`php -l` によるいずれのPHPファイルの構文チェックも実行できなかった。代わりに、全PHPプリアンブル・`seo_meta.html`・コントローラ差分を目視で静的解析し、`isset()`/`empty()` による未定義変数ガード、CakePHPコントローラ側での `$box`/`$category`/`$target`/`$target_id` の設定保証(`ezmError('error404')` による早期終了を含む)を個別に確認した。**本番反映前に、PHPが使える環境で全対象ファイルの `php -l` を実行することを強く推奨する。**
- **Python未インストール**: `python`/`python3`/`py` のいずれも実行できず(WindowsAppsのストア誘導スタブのみ存在)、`tools/validate_seo_update.py` を実行できなかった。同スクリプトが行う全チェック項目を手動で(grep等により)個別に再現・確認したが(結果は下記「検証結果」)、スクリプト実行による最終確認は未実施。
- **Node.js未インストール**: `node`/`npm` が無く、`temporary_preview_site` のビルド・PC幅/スマートフォン幅での実描画確認は実施できなかった。
- **works以外のカテゴリのpage:1重複**: 上記「発見した問題 2.」参照。本番相当環境での確認が必要。
- **id=21/22のカテゴリ順序の実データ確認**: 上記「発見した問題 3.」参照。DBの並び順が変わった場合、正規URL判定に影響する可能性がある。

## 検証結果

実行できなかった項目(PHP/Python/Node)を除き、以下は静的検証で確認した。

| 項目 | 結果 |
|---|---|
| `php -l` | **未実施**(PHP未インストールのため。上記参照) |
| `tools/validate_seo_update.py` の実行 | **未実施**(Python未インストールのため)。同スクリプトの各チェックを手動で再現し、全て合格を確認(下記詳細) |
| sitemap.xmlのXML妥当性 | `<url>`47・`</url>`47・`<loc>`47・`<urlset>`/`</urlset>`各1、タグ数の不整合なし。`index.html`・`page:1`を含まない |
| sitemap.xmlの正規URL数 | 47件、重複なし(`sort -u`で47件のまま) |
| robots.html | `/media/` を disallow していないことを確認。`/admin/`, `/admin_sp/`, `/data_files/`, `/catalog_preview/`, `/_bk_20221124/`, `/_dl/`, `/SampleKit/`, `/securimage/example_form`, `/ez_js/eq/`, `/ez_js/pdf/web/`, `/maintenance.html` を disallow |
| H1数(全対象テンプレート) | Homes/index, webroot/business, webroot/contact, catalog cl01_2/index, cl01_3/index, cl02_4/index, cl02_4/view, Contact/msg, Contact/thanks, Errors/error400 の全10ファイルで `<h1` が正確に1個 |
| ヘッダーロゴがH1でないこと | 全テンプレートで `<h1 class="osu3">` 型の旧ロゴ表記が0件、`class="site-logo osu3"` の新表記に統一されていることを確認 |
| canonical/OGP/Twitter Card/JSON-LD | `seo_meta.html` に `rel="canonical"`, `og:title`等, `twitter:card`, `application/ld+json`, Organization/WebSite/BreadcrumbList の各`@type`が存在することを確認。会社ページのみ `AboutPage`/`CollectionPage` を `$seoIsRoot` で分岐していることを確認 |
| ホームのLCP画像 | `loading="lazy"` が付いておらず、`fetchpriority="high"`、`decoding="async"` は1個のみであることを確認(`finalize_seo_update.py` のバグ修正が適用済みの状態で現行ファイルに反映されていることを確認) |
| 2019〜2026年 主な実績 | 会社ページに存在することを確認 |
| 近年実績85件 | `class="achievement-list__item"` が正確に85件であることを確認 |
| 削除済み文言の非再出現 | 「アーティスト協会 MUSICIAN事業部として継続している実績を含みます。」が会社ページに存在しないことを確認 |
| COVID時期の文言 | 「緊急事態宣言などでライブ開催が難しかった期間は、配信・映像制作を活用して活動を継続しました。その後は状況の緩和に合わせ、通常のライブ、公演、出張演奏を段階的に再開しています。」という記述を確認。恒久的な事業転換ではなく、通常営業への復帰と整合する表現になっている |
| CakePHP未定義変数リスク | `seo_meta.html` は全変数を `isset()`/`empty()` でガード。動的テンプレートの `extract($box['CatalogBox'], ...)` 等は、対応するコントローラ(`WorksController`/`CompanyController`/`ArtistController`)側で `$box`/`$category`/`$target`/`$target_id` が必ず設定される(未設定時は `ezmError('error404')` で早期終了)ことをコントローラのソースで確認 |
| ルーティングの404 | `app/Config/routes.php` に追加した `/:slug.html` 汎用404ルートは、`webroot_routing()` (webroot配下の全 `.html` を先に個別ルート登録する既存関数、`admin/Vendor/util.php` に定義)より後に登録されているため、実在する静的ページ(business.html, contact.html等)のルーティングを妨げないことを確認 |
| 管理画面への影響 | 追加した`.htaccess`ルール・routes.phpのルールはいずれも特定の静的パスのみに一致し、`/admin`系の既存の(コメントアウトも含む)ルーティング動作を変更していないことを確認 |
| error400.html | CakePHPのエラー用レイアウト(`Layouts/error.html`)が `$this->fetch('content')` のみであり、独自の`<html>`/`<body>`を持たないため、新しい`error400.html`が単独で完全なHTML文書を出力しても二重ラップにならないことを確認 |

## 変更したファイル一覧

- `tools/build_seo_update.py`(編集: 正規表現処理を2箇所修正・統合)
- `tools/run_build_seo_update.py`(削除)
- `tools/run_build_seo_update_final.py`(削除)
- `tools/__pycache__/run_build_seo_update.cpython-312.pyc`(削除、キャッシュ)
- `tools/__pycache__/run_build_seo_update_final.cpython-312.pyc`(削除、キャッシュ)
- `new_site/seo_deployment/README.md`(編集: ビルド手順の明記)
- `new_site/seo_deployment/CLAUDE_REVIEW.md`(新規作成、本ファイル)

`new_site/seo_deployment` 配下の19ファイル(HTML/PHP/.htaccess/sitemap.xml等)、`temporary_preview_site` のプレビュー資産(`app/seo/*`, `public/seo.html`, `public/seo-preview.css`, `public/company.html`, `public/css/style.css`)には変更を加えていない。

## 本番反映時の注意事項

1. 本番反映前に、PHP/Python/Node.jsが使える環境で以下を必ず実行し、全て合格することを確認すること。
   - `php -l`(`new_site/seo_deployment` 配下の全 `.php`/`.html`(PHPテンプレート)ファイル)
   - `python tools/build_seo_update.py && python tools/finalize_seo_update.py && python tools/validate_seo_update.py`
   - `temporary_preview_site` のビルドとPC幅/スマートフォン幅での目視確認
2. company側サブカテゴリ(id: 5,6,7,12〜20)に `page:1` の重複URLが実在しないか、本番相当環境で確認すること(「未解決事項」参照)。
3. `.htaccess` の新規リダイレクトルールは外部リダイレクト(R=301)であり、ブラウザ側で新規リクエストとして処理されるため無限ループの懸念はないが、反映直後は実URLで直接疎通確認すること(`/index.html`, `/works/index/22`, `/company/index/21`, `/works/index/4/page:1`, `/works/index/25/page:1`)。
4. 存在しない `.html` へのアクセス(例: `/nonexistent.html`)が実際に404を返すこと、かつ既存の実在ページ(business.html, contact.html等)が影響を受けないことを反映直後に確認すること。
5. sitemap.xml・robots.txtの内容は本番反映後、実URLで最終確認すること(PHP側の `<?php if (Configure::read('debug') > 0) ?>` 分岐により、本番の `debug` 設定が0でない場合は `robots.txt` が全面 `Disallow: /` になる点に注意)。

## SSL復旧後に確認すべき項目

1. `https://www.musician.co.jp/sitemap.xml` が正しく配信されることを確認したうえで、Google Search Console・Bing Webmaster Toolsへsitemapを再送信する。
2. 各主要ページのcanonical URL・OGP画像URLが `https://www.musician.co.jp/...` で実際に到達可能であることを確認する(現状はURLをハードコードしているため、SSL有効化前後でURLの実体は変わらないはずだが、証明書混在期間中のブラウザ警告・混在コンテンツの有無を確認)。
3. JSON-LD(Organization/WebSite/WebPage/AboutPage/CollectionPage/ProfilePage/BreadcrumbList/Service)をGoogleのリッチリザルトテスト等で再検証する。
4. SNS(Facebook/X/LINE)でのシェアプレビューが OGP/Twitter Card 通りに表示されることを確認する。
5. 独自ドメインでのHTTPS強制(`.htaccess` の `RewriteCond %{ENV:HTTPS} !^on$` 部分)が証明書適用後に意図通り動作し、リダイレクトループが発生しないことを確認する。
