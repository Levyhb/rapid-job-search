function Use-RapidJobNode {
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $minimum = [version](Get-Content (Join-Path $projectRoot '.node-version') -Raw).Trim()
    $portable = Join-Path $projectRoot "work/security-runtimes/node-v$minimum-win-x64/node.exe"
    $candidate = if (Test-Path -LiteralPath $portable) {
        $portable
    } else {
        (Get-Command node.exe -ErrorAction Stop).Source
    }
    $installed = [version](Get-Item -LiteralPath $candidate).VersionInfo.ProductVersion
    if ($installed.Major -ne 24 -or $installed -lt $minimum) {
        throw "Use Node.js 24 com patch >= $minimum. Versao encontrada: $installed."
    }
    # Alteração apenas neste processo; preserva a instalação global e os outros projetos.
    $env:PATH = (Split-Path $candidate -Parent) + [IO.Path]::PathSeparator + $env:PATH
}

function Assert-RapidJobPython {
    param([Parameter(Mandatory = $true)][string]$Executable)
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $minimum = (Get-Content (Join-Path $projectRoot '.python-version') -Raw).Trim()
    & $Executable -I -c 'import sys; minimum=tuple(map(int,sys.argv[1].split("."))); sys.exit(0 if sys.version_info[:2] == (3,14) and sys.version_info[:3] >= minimum else 1)' $minimum
    if ($LASTEXITCODE -ne 0) {
        throw "Use Python 3.14 com patch >= $minimum. Atualize o runtime e o ambiente virtual."
    }
}

function Get-RapidJobPython {
    $projectRoot = Split-Path $PSScriptRoot -Parent
    $minimum = (Get-Content (Join-Path $projectRoot '.python-version') -Raw).Trim()
    $portable = Join-Path $projectRoot "work/security-runtimes/python-$minimum/python.exe"
    $candidate = if (Test-Path -LiteralPath $portable) {
        $portable
    } else {
        & py -3.14 -I -c 'import sys; print(sys.executable)'
    }
    Assert-RapidJobPython -Executable $candidate
    return $candidate
}
