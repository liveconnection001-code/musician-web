# MUSICIAN GitHub公開運用

更新日: 2026-07-28

## 正規版

- GitHub: `https://github.com/liveconnection001-code/musician-web`
- 本番公開ブランチ: `main`
- ローカル作業場所: `A:\AI\Web\MUSICIAN`
- 本番サイト: `https://www.musician.co.jp/`

以後、サイトの正規版はGitHubの`main`です。ファイルマネージャー上で直接
編集した内容は正規版にならず、次の公開で上書きされるため使用しません。

## Codexへ更新を依頼したときの標準手順

1. `MUSICIAN_DESIGN_GUIDELINES.md`と現在の本番を確認する。
2. ローカルで変更し、PC・携帯のプレビューを確認する。
3. ページ、画像、リンク、SEO、セキュリティの自動検査を通す。
4. 変更をGitへコミットし、`main`へpushする。
5. GitHub Actions `deploy-musician-production`の完了を待つ。
6. 本番を再検査し、正常表示を確認して完了する。

日常の更新では、利用者がPowerShellやFTPパスワードを入力する必要はありません。

## GitHub Actionsが自動で行うこと

- 公開前にAbout us、Achievements、Artist、Works、SEOを検査
- 現在の本番ファイルをロールバック用に保存
- 変更ファイルをFTPへ原子的に公開し、ハッシュを照合
- 公開後に主要ページ、リダイレクト、画像・実績・SEO・防御設定を検査
- 公開後検査に失敗した場合は直前の本番へ自動復元
- 成功した場合だけ一時アップロード・旧バックアップ・旧CMS残骸を削除
- ロールバックスナップショットをGitHubへ90日間保存
- 同時公開を禁止し、1回ずつ順番に処理

## 確認場所

GitHubの `Actions` → `deploy-musician-production` で、最新の実行が緑色の
チェックになっていることを確認します。赤色の場合は再実行を重ねず、Codexへ
その実行番号を伝えて原因を直します。

## 復元基準

- Gitタグ: `production-YYYY-MM-DD`
- ローカル完全Gitバックアップ: `release_backups/*.bundle`
- 内容一覧とハッシュ: `release_backups/*/manifest.json`
- GitHub Actionsのロールバック成果物: 90日間

通常の復元もCodexへ依頼し、推測で古いファイルをアップロードしません。

## 例外

ローカルからの直接FTP公開は、GitHubが長時間利用不能な場合の緊急復旧だけに
限定します。通常公開で`tools/run_github_default_ops.ps1 -Action deploy-full`
は使用しません。
