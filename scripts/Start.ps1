param([string]$InstallRoot = (Join-Path $env:USERPROFILE 'Documents/Codex/DevTools/apps/PDFMathTranslate/2.9.0-safety-v1'))
$ErrorActionPreference = 'Stop'
$appDirectory = Join-Path $InstallRoot 'pdf2zh'
$appExe = Join-Path $appDirectory 'pdf2zh.exe'
if (-not (Test-Path -LiteralPath $appExe)) { throw 'Install the tool first with scripts/Install.ps1.' }
$runningApp = Get-Process -Name pdf2zh -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $appExe }
if (-not $runningApp) {
    $logDirectory = Join-Path $InstallRoot 'logs'
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    Start-Process -FilePath $appExe -WorkingDirectory $appDirectory -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'stdout.log') -RedirectStandardError (Join-Path $logDirectory 'stderr.log') | Out-Null
}
Write-Output 'PDFMathTranslate is starting or already running: http://127.0.0.1:7860/'
