# 1回で実行できるGitHub運用スクリプト

## デフォルト運用（mainを公開ブランチ、developで作業）

- リモート追跡確認: `git remote -v`
- 開発作業は基本 `develop` で実施
- スナップショット更新: `powershell -File tools\run_github_default_ops.ps1 -Action snapshot`
- develop へ反映後: `git add -A ; git commit -m "..." ; git push -u origin develop`
- 本番反映（mainへ反映）:
  `powershell -File tools\git_publish_default.ps1 -Snapshot`
  （`-Snapshot` は任意。付けると本番前に快適用 snapshot を1回採ります）
- さらにGitHub公開をローカル同等で即時実行する場合: `powershell -File tools\git_publish_default.ps1 -Snapshot -Deploy`

## ローカル直接公開

- スナップショット更新: `powershell -File tools\run_github_default_ops.ps1 -Action snapshot`
- 本番フル反映: `powershell -File tools\run_github_default_ops.ps1 -Action deploy-full`
- SEOのみ反映: `powershell -File tools\run_github_default_ops.ps1 -Action deploy-seo`
- Achievementsのみ反映: `powershell -File tools\run_github_default_ops.ps1 -Action deploy-achievements`

## GitHub上の実行（推奨）

- main push で自動実行されるデプロイワークフロー: `deploy-musician-production`
- Actions → ワークフロー → `Run workflow` で手動起動も可能
