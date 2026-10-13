param(
    [string]$InstallRoot = (Join-Path $env:USERPROFILE 'Documents/Codex/DevTools/apps/PDFMathTranslate/2.9.0-safety-v1'),
    [string]$ArchivePath
)
$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$release = Get-Content -LiteralPath (Join-Path $repositoryRoot 'release.lock.json') -Raw | ConvertFrom-Json
$appDirectory = Join-Path $InstallRoot 'pdf2zh'
$appExe = Join-Path $appDirectory 'pdf2zh.exe'
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $appExe)) {
    $cacheDirectory = Join-Path $InstallRoot 'downloads'
    New-Item -ItemType Directory -Path $cacheDirectory -Force | Out-Null
    if (-not $ArchivePath) { $ArchivePath = Join-Path $cacheDirectory $release.asset_name }
    if (-not (Test-Path -LiteralPath $ArchivePath)) { Invoke-WebRequest -Uri $release.url -OutFile $ArchivePath }
    if ((Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $release.sha256) { throw 'The downloaded release archive failed SHA256 verification.' }
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $InstallRoot
    if (-not (Test-Path -LiteralPath $appExe)) { throw 'The release archive did not contain the expected pdf2zh/pdf2zh.exe.' }
}
$runtimePython = Join-Path $appDirectory 'runtime/python.exe'
& $runtimePython (Join-Path $PSScriptRoot 'manage_patch.py') apply --app-dir $appDirectory
if ($LASTEXITCODE -ne 0) { throw 'The patch manager refused this installation. No private settings were changed.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Start.ps1') -Destination (Join-Path $InstallRoot 'Start-PDFMathTranslate.ps1')
$shortcutShell = New-Object -ComObject WScript.Shell
$shortcut = $shortcutShell.CreateShortcut((Join-Path $InstallRoot 'PDFMathTranslate.lnk'))
$shortcut.TargetPath = $appExe
$shortcut.WorkingDirectory = $appDirectory
$shortcut.WindowStyle = 7
$shortcut.Description = 'Persistent PDFMathTranslate installation with scientific-document safety patches'
$shortcut.Save()
Write-Output "Persistent installation ready: $appDirectory"
Write-Output "Start with: $InstallRoot/Start-PDFMathTranslate.ps1"
