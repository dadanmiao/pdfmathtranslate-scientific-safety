param(
    [string]$InstallRoot = (Join-Path $env:USERPROFILE 'Documents/Codex/DevTools/apps/PDFMathTranslate/2.9.0-safety-v1'),
    [switch]$Pipeline,
    [string]$SourcePdf
)
$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$appDirectory = Join-Path $InstallRoot 'pdf2zh'
$runtimePython = Join-Path $appDirectory 'runtime/python.exe'
$env:PDF2ZH_APP_DIR = $appDirectory
$env:PDF2ZH_TEST_OUTPUT = Join-Path $repositoryRoot 'artifacts'
& $runtimePython (Join-Path $PSScriptRoot 'manage_patch.py') verify --app-dir $appDirectory
if ($LASTEXITCODE -ne 0) { throw 'Patch verification failed.' }
& $runtimePython -m unittest discover -s (Join-Path $repositoryRoot 'tests') -p test_patch_manager.py
if ($LASTEXITCODE -ne 0) { throw 'Deployment tests failed.' }
& $runtimePython (Join-Path $repositoryRoot 'tests/test_scientific_safety.py')
if ($LASTEXITCODE -ne 0) { throw 'Scientific safety tests failed.' }
if ($Pipeline) {
    $pipelineArguments = @((Join-Path $repositoryRoot 'tests/pipeline_regression.py'))
    if ($SourcePdf) { $pipelineArguments += @('--source-pdf', (Resolve-Path -LiteralPath $SourcePdf).Path) }
    & $runtimePython @pipelineArguments
    if ($LASTEXITCODE -ne 0) { throw 'Pipeline regression failed.' }
}
