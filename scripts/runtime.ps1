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
