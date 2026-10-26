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
        & .venv/Scripts/python.exe -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel preparar o banco. Inicie a infraestrutura com .\scripts\dev.ps1 infra.' }
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
