# MUSICIAN GitHub公開運用：今日からの最短実行手順

このフォルダを既存データで初期化できることを前提に、
「GitHubを真のデフォルト」にする運用を始めるための実行順をまとめます。

前提:
- .github/workflows/deploy-production.yml がある
- tools/capture_site_snapshot.py がある
- deploy_*_production.py は WORKSPACE を環境変数で解決

## 1) 初期化（A: スナップショットの固定）
1. `python` が使えない環境では既存Pythonを使う

```powershell
& 'C:\Users\Takashi Miyazaki\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'A:\AI\Web\MUSICIAN\tools\capture_site_snapshot.py'
```

2. これで `default_snapshots/latest.json` が更新されます。

## 2) GitHubブランチ運用（B: 並行）
- 作業ブランチ: `develop`
- 本番反映: `main`
- 変更は原則 `develop` → PR/マージで `main`

## 3) 既存運用と並行した手動デプロイ（必要時）
- 既存の手動公開手順は維持
- GitHub CI公開は追加運用として併用

## 4) CI自動公開（C）
### 4-1. `main` 更新で自動実行
- `main` への push で `deploy-production` が走る
- GitHub Secrets: `MUSICIAN_TEMP_FTP_PASSWORD` を必ず登録

### 4-2. 手動実行
- Actions → `deploy-musician-production` → `Run workflow`

## 5) ローカルから同じ手順を再現（テスト/緊急復旧向け）
```powershell
$env:MUSICIAN_WORKSPACE = 'A:\\AI\\Web\\MUSICIAN'
$env:MUSICIAN_TEMP_FTP_PASSWORD = '***'
& 'C:\Users\Takashi Miyazaki\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'A:\\AI\\Web\\MUSICIAN\\tools\\deploy_full_production.py' deploy
```

## 6) ロールバック
- 失敗時の現地復旧履歴は
  `new_site/production_backups/<stamp>/manifest.json`
  を見て、必要なら前回の内容を復旧

---

最終チェック（公開後）
- 青い帯/Works/Business/Artist/About us/Achievements の見た目が崩れていないか
- AchievementsのURLと導線
- 404やリンク切れ、画像ファイル不足
- `snapshot latest` と差分で変更点を記録
