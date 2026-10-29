$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Checked {
    param([scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Verificação falhou com código $LASTEXITCODE" }
}

Push-Location backend
try {
    Invoke-Checked { & .venv/Scripts/python.exe -m ruff check . }
    Invoke-Checked { & .venv/Scripts/python.exe -m pytest }
} finally { Pop-Location }
Push-Location frontend
try {
    Invoke-Checked { npm.cmd run lint }
    Invoke-Checked { npx.cmd next typegen }
    Invoke-Checked { npx.cmd tsc --noEmit }
    Invoke-Checked { npm.cmd run build }
} finally { Pop-Location }
Invoke-Checked { docker compose config --quiet }
