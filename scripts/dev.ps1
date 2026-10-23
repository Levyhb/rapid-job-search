param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('api', 'frontend', 'infra', 'worker')]
    [string]$Service
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
switch ($Service) {
    'api' {
        Set-Location backend
        & .venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    }
    'frontend' {
        Set-Location frontend
        npm.cmd run dev -- --hostname 127.0.0.1
    }
    'infra' { docker compose up -d --wait postgres redis }
    'worker' { docker compose --profile worker up --build worker }
}
exit $LASTEXITCODE
