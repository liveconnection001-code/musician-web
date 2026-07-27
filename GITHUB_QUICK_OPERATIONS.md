# 1回で実行できるGitHub運用スクリプト

- スナップショット更新: `powershell -File tools\run_github_default_ops.ps1 -Action snapshot`
- 本番フル反映: `powershell -File tools\run_github_default_ops.ps1 -Action deploy-full`
- SEOのみ反映: `powershell -File tools\run_github_default_ops.ps1 -Action deploy-seo`
- Achievementsのみ反映: `powershell -File tools\run_github_default_ops.ps1 -Action deploy-achievements`
