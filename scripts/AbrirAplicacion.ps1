param([string]$Base)
$ErrorActionPreference = 'Stop'
$tandemRoot = Split-Path -Parent $PSScriptRoot
$tandemPython = Join-Path $tandemRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $tandemPython)) {
    throw 'Falta el entorno Python. Ejecuta scripts\Preparar.ps1.'
}
$tandemArguments = @('-m', 'tandem.app')
if ($Base) { $tandemArguments += @('--db', ('"' + $Base + '"')) }
Start-Process -FilePath $tandemPython -ArgumentList $tandemArguments -WorkingDirectory $tandemRoot -WindowStyle Hidden
