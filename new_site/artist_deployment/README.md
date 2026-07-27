# 大町めぐみ Artist更新（公開前ステージング）

このフォルダは、MUSICIANのArtist更新を公開前に確認するための一式です。まだ本番サーバーへはアップロードしていません。

## 変更内容

- Artist一覧で大町めぐみ（ID 62）を「所属アーティスト」へ移動
- トップページのハンドベル「Holly Bell」（ID 51）の位置を、大町めぐみに置換
- `/artist/view/62` を専用プロフィールページへ拡充
- 本人指定の宣材写真10枚によるクリック拡大ギャラリー
- 本人指定のYouTube演奏動画
- 最新経歴（上海音楽学院へ2年間留学・2026年に進修課程修了）、受賞、リリース、レパートリー、出演依頼、公式SNS
- ProfilePage / Person構造化データ、個別title・description・OG画像
- 掲載用写真のEXIF・位置情報を再書き出しで除去

## 公開時の配置

- `app/View/Homes/index.html`
- `app/View/catalog/cl02_4/default/index.html`
- `app/View/catalog/cl02_4/default/view.html`
- `app/webroot/css/artist_megumi.css`
- `app/webroot/images/artists/megumi-omachi/` 以下すべて

## 確認

`tools/verify_artist_release.py` で、10枚のギャラリー、YouTube・SNS、最新プロフィール、トップ枠、所属分類、SEO、社名表記、必要素材、EXIF除去を検証できます。

## 表記ルール

- サイト・サービス名: `MUSICIAN`
- 会社名: `株式会社東京アーティスト協会`
- 使用禁止: `株式会社MUSICIAN`

