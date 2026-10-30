$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'runtime.ps1')
Use-RapidJobNode
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Checked {
    param([scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Comando falhou com código $LASTEXITCODE" }
}

if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (-not (Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
if (-not (Test-Path backend/.venv/Scripts/python.exe)) {
    $pythonRuntime = Get-RapidJobPython
    Invoke-Checked { & $pythonRuntime -I -m venv backend/.venv }
}
Assert-RapidJobPython -Executable (Join-Path (Get-Location) 'backend/.venv/Scripts/python.exe')
Invoke-Checked { & backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.lock }
Invoke-Checked { & backend/.venv/Scripts/python.exe -m pip install --no-deps -e './backend[dev]' }
Invoke-Checked { & backend/.venv/Scripts/python.exe -m playwright install chromium }
Push-Location frontend
try { Invoke-Checked { npm.cmd ci } } finally { Pop-Location }
Invoke-Checked { docker compose up -d --wait postgres redis }
Push-Location backend
try { Invoke-Checked { & .venv/Scripts/python.exe -m alembic upgrade head } } finally { Pop-Location }
Write-Host 'Ambiente preparado. Execute .\scripts\dev.ps1 api e .\scripts\dev.ps1 frontend em terminais separados.'
