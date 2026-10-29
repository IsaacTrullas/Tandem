$ErrorActionPreference = 'Stop'
$tandemRoot = Split-Path -Parent $PSScriptRoot
$tandemPython = Join-Path $tandemRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $tandemPython)) {
    throw 'Falta el entorno Python. Ejecuta scripts\Preparar.ps1.'
}
Push-Location $tandemRoot
try {
    & $tandemPython -m tandem @args
    $tandemExit = $LASTEXITCODE
}
finally { Pop-Location }
exit $tandemExit
