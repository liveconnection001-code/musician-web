# MUSICIAN GitHub運用・最短メモ

1. ホームページの変更内容をCodexへ指示する。
2. Codexがプレビュー・自動検査・Gitコミット・GitHub pushを行う。
3. GitHub Actionsがバックアップ後に本番公開する。
4. 公開後検査が成功した場合だけ旧一時ファイルを削除する。
5. Actionsが失敗した場合は自動復元し、Codexが原因を修正する。

正規版は`main`、公開ワークフローは`deploy-musician-production`です。
通常はPowerShell、FTP、ファイルマネージャーを利用者が操作する必要はありません。

詳細は`GITHUB_OPERATING_RUNBOOK.md`を参照してください。
