param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('develop','main')]
  [string]$Mode
)

$ErrorActionPreference = 'Stop'

$workspace = 'A:\AI\Web\MUSICIAN'
$python = 'C:\Users\Takashi Miyazaki\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:MUSICIAN_WORKSPACE = $workspace
$env:PYTHONIOENCODING = 'utf-8'

switch ($Mode) {
  'develop' {
    & $python (Join-Path $workspace 'tools/capture_site_snapshot.py')
    Write-Host 'Snapshot updated for develop.'
  }
  'main' {
    if (-not $env:MUSICIAN_TEMP_FTP_PASSWORD) {
      throw 'MUSICIAN_TEMP_FTP_PASSWORD が未設定です。'
    }
    & $python (Join-Path $workspace 'tools/deploy_full_production.py') 'deploy'
  }
}
