param(
  [ValidateSet('snapshot','deploy-full','deploy-seo','deploy-achievements')][string]$Action
)

$ErrorActionPreference = 'Stop'
$ROOT = 'A:\AI\Web\MUSICIAN'
$PY = 'C:\Users\Takashi Miyazaki\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:MUSICIAN_WORKSPACE = $ROOT

function Invoke-Deploy([string]$Script, [string[]]$Arguments) {
  & $PY (Join-Path $ROOT $Script) @Arguments
}

switch ($Action) {
  'snapshot' {
    Invoke-Deploy 'tools/capture_site_snapshot.py' @()
  }
  'deploy-full' {
    if (-not $env:MUSICIAN_TEMP_FTP_PASSWORD) { throw 'MUSICIAN_TEMP_FTP_PASSWORD is required for deployment.' }
    Invoke-Deploy 'tools/deploy_full_production.py' @('deploy')
  }
  'deploy-seo' {
    if (-not $env:MUSICIAN_TEMP_FTP_PASSWORD) { throw 'MUSICIAN_TEMP_FTP_PASSWORD is required for deployment.' }
    Invoke-Deploy 'tools/deploy_seo_production.py' @('deploy')
  }
  'deploy-achievements' {
    if (-not $env:MUSICIAN_TEMP_FTP_PASSWORD) { throw 'MUSICIAN_TEMP_FTP_PASSWORD is required for deployment.' }
    Invoke-Deploy 'tools/deploy_achievements_production.py' @('deploy')
  }
}

