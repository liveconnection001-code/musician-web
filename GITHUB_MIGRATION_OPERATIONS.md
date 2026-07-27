# GitHub運用（最小構成）: A/B/C 実施手順

日付: 2026-07-27  
目的: 「今の状態」を唯一の基準版として固定し、更新差分が戻る事故を減らす

## A. まずこの状態をスナップショット化（1回だけ）

1. 以下を「デフォルト状態」として固定
- `new_site/deployment/`（実績欄差分の業務ルート）
- `new_site/seo_deployment/`（SEO/タイトル/OGP/ルート）
- `new_site/works_deployment/`（Works ギャラリー）
- `new_site/artist_deployment/`（所属アーティスト領域）
2. 現在の状態を記録
- `python tools/capture_site_snapshot.py` を実行し、`default_snapshots/` に
  `latest.json` と `snapshot-YYYYMMDDTHHMMSS.json` を生成
- `production_backups/` や各種 manifest が同時に参照できるため、復元時の比較が容易

## B. バックアップ保全とGitHub運用を並行で始める

1. バックアップは従来どおり残す
- `tools/deploy_full_production.py`, `tools/deploy_seo_production.py`,
  `tools/deploy_achievements_production.py` はデプロイ時に
  `new_site/production_backups/` へローカルロールバック情報を保存
- 既存運用は停止せず、手動デプロイ権限も維持

2. GitHub側で「truth source」を固定
- まずは `main` だけが本番公開対象
- `develop`（または `staging`）で作業し、`main` は最終確定のみ反映
- 変更は `review -> snapshot update -> merge` の順序で固定

3. リスク分離
- `snapshot` 更新は必ず別コミットで残す
- `review` と `upload` の作業を同一コミットにまとめず、あとで巻き戻しやすくする

## C. CI公開までの設計

### 推奨フロー
- `main` への push または手動実行で GitHub Actions を起動
- `python tools/deploy_full_production.py deploy` を実行
- 環境変数 `MUSICIAN_TEMP_FTP_PASSWORD` と `MUSICIAN_WORKSPACE` を使って
  既存の FTP デプロイスクリプトに一本化

### 事故時対応
- 失敗時は既存デプロイスクリプトがロールバック情報を残し、復元しやすい状態を維持
- `new_site/production_backups/<stamp>/manifest.json` を確認し、復旧コマンドを再実行

## 1〜5 進め方（今回の運用ルール）

1. まず「デフォルト状態」を1回だけスナップショット化
2. 以後の作業は `develop` 側で積み上げ
3. サイト公開前に `snapshot` を更新して比較ポイントを固定
4. 本番公開前に `main` へマージし、CIで自動公開
5. 公開後は `snapshot latest` と差分確認（ヘッダー/ナビ/青ライン/画像リンク）を必ず実施

## 運用チェック（公開前に毎回）
- `deploy-production.yml` が成功
- `tools/deploy_full_production.py` の実行ログに `backed up` と `verification` があること
- `新しいページ / 既存リンク / 青ライン / ファイル参照` の整合性（公開前プレビュー）

## 追加: 開発ブランチ運用（実運用）

- 開発: `develop`
- 本番: `main`

### 日次運用
1. 変更作業は `develop` で実施
2. スナップショット更新: `tools/run_github_default_ops.ps1 -Action snapshot`
3. 最終確認後に `develop` → `main` に統合
4. `main` push または Action 手動実行で公開

### CIの起動ルール
- `main` push 時のみ自動公開
- 緊急修正は `main` で直接実施せず、まず `develop` 反映を推奨

### 監査ログの最小セット
- 最新スナップショット: `default_snapshots/latest.json`
- ロールバック: `new_site/production_backups/*/manifest.json`
- 実行ログ: GitHub Actions のデプロイジョブ

### 失敗したときの最短復旧
- 失敗時: `main` に再デプロイを重ねず、`new_site/production_backups` の直近 manifest を確認
- 既存手動運用（deploy_*）に切替えて1回限定で復旧
- 原因は同一コミットで再利用しない
