param([Parameter(Mandatory=$true)][string]$Manifiesto)
$ErrorActionPreference = 'Stop'
$tandemRoot = Split-Path -Parent $PSScriptRoot
$tandemPython = Join-Path $tandemRoot '.venv\Scripts\python.exe'
$tandemManifest = (Resolve-Path -LiteralPath $Manifiesto).Path
$tandemRun = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
Push-Location $tandemRoot
try {
    $tandemSteps = @(
        @('sync', $tandemManifest),
        @('ocr'),
        @('extract-pdf'),
        @('audit', '--output', "data/auditorias/$tandemRun.json"),
        @('backup', "data/backups/final_$tandemRun.sqlite")
    )
    foreach ($tandemStep in $tandemSteps) {
        & $tandemPython -m tandem @tandemStep
        if ($LASTEXITCODE -ne 0) { throw "Falló el paso $($tandemStep[0]); actualización incompleta." }
    }
}
finally { Pop-Location }
