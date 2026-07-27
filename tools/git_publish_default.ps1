param(
  [switch]$Snapshot,
  [switch]$Deploy,
  [string]$Remote = 'origin'
)

$ErrorActionPreference = 'Stop'
$workspace = 'A:\AI\Web\MUSICIAN'
$python = 'C:\Users\Takashi Miyazaki\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

Set-Location $workspace
$env:MUSICIAN_WORKSPACE = $workspace

& git fetch $Remote

if ($Snapshot) {
  Write-Host '[1/4] Snapshot update'
  & $python (Join-Path $workspace 'tools/capture_site_snapshot.py')
}

Write-Host '[2/4] develop -> push'
& git switch develop
& git push $Remote develop

Write-Host '[3/4] main <- develop のマージ and push'
& git switch main
& git merge --ff-only "$Remote/develop"
& git push $Remote main

if ($Deploy) {
  Write-Host '[4/4] ローカル同等で本番公開を実行'
  if (-not $env:MUSICIAN_TEMP_FTP_PASSWORD) {
    throw 'MUSICIAN_TEMP_FTP_PASSWORD が未設定です。'
  }
  & $python (Join-Path $workspace 'tools/deploy_full_production.py') 'deploy'
}

Write-Host 'Done.'
