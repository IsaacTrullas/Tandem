param([switch]$SinOCR)
$ErrorActionPreference = 'Stop'
$tandemRoot = Split-Path -Parent $PSScriptRoot
$tandemVenv = Join-Path $tandemRoot '.venv'
$tandemPython = Join-Path $tandemVenv 'Scripts\python.exe'
Push-Location $tandemRoot
try {
    if (-not (Test-Path -LiteralPath $tandemPython)) {
        $tandemBootstrap = Get-Command python -ErrorAction SilentlyContinue
        if (-not $tandemBootstrap) { throw 'Se necesita Python 3.11 o posterior en PATH.' }
        & $tandemBootstrap.Source -m venv $tandemVenv
        if ($LASTEXITCODE -ne 0) { throw 'No se ha podido crear el entorno.' }
    }
    $tandemPackage = if ($SinOCR) { '.' } else { '.[ocr]' }
    & $tandemPython -m pip install -e $tandemPackage
    if ($LASTEXITCODE -ne 0) { throw 'No se han podido instalar las dependencias.' }
    & $tandemPython -m tandem init
    if ($LASTEXITCODE -ne 0) { throw 'No se ha podido inicializar la base.' }
}
finally { Pop-Location }
