"""Verificações locais sem rede; nunca imprimir valores de possíveis segredos."""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[\w]{30,})\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
}


def runtime_policy():
    errors = []
    node = (ROOT / ".node-version").read_text().strip()
    python = (ROOT / ".python-version").read_text().strip()
    node_parts = tuple(map(int, node.split(".")))
    python_parts = tuple(map(int, python.split(".")))
    if node_parts < (24, 22, 1) or node_parts[0] != 24:
        errors.append(".node-version: patch de segurança da linha 24 obrigatório")
    if python_parts < (3, 14, 10) or python_parts[:2] != (3, 14):
        errors.append(".python-version: patch de segurança da linha 3.14 obrigatório")
    package = json.loads((ROOT / "frontend/package.json").read_text())
    lock = json.loads((ROOT / "frontend/package-lock.json").read_text())
    engines = {"node": f">={node} <25"}
    if package.get("engines") != engines or lock["packages"][""].get("engines") != engines:
        errors.append("frontend: engines e lock devem acompanhar .node-version")
    if "engine-strict=true" not in (ROOT / "frontend/.npmrc").read_text().splitlines():
        errors.append("frontend/.npmrc: verificação estrita do runtime obrigatória")
    dockerfile = (ROOT / "backend/Dockerfile").read_text()
    if dockerfile.splitlines()[0] != f"FROM python:{python}-slim":
        errors.append("Dockerfile: alinhar patch com .python-version")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    for action in re.findall(r"uses:\s*(\S+)", workflow):
        if not re.fullmatch(r"[\w.-]+/[\w.-]+@[a-f0-9]{40}", action):
            errors.append("CI: action deve usar SHA completo")
    for expected in ("node-version-file: '.node-version'", "python-version-file: '.python-version'"):
        if expected not in workflow:
            errors.append("CI: runtime deve vir do arquivo de versão do projeto")
    names = set()
    for line in (ROOT / "backend/requirements.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([\w.-]+)==[\w.+!-]+", line)
        if not match:
            errors.append("requirements.txt: usar somente versões exatas, sem comandos/URLs")
            continue
        name = re.sub(r"[-_.]+", "-", match[1]).lower()
        if name in names:
            errors.append("requirements.txt: pacote duplicado")
        names.add(name)
    return errors


def secret_policy():
    listing = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    errors = []
    for name in sorted(set(filter(None, listing))):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            continue
        content = path.read_bytes()
        if b"\0" in content:  # Não alegar cobertura de formatos binários.
            continue
        for number, line in enumerate(content.decode("utf-8", errors="replace").splitlines(), 1):
            for rule, pattern in SECRET_PATTERNS.items():
                if pattern.search(line):
                    errors.append(f"{name}:{number}: possível segredo ({rule}); valor omitido")
    return errors


def main():
    try:
        errors = runtime_policy() + secret_policy()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print("Verificação de segurança não concluída; confira Git, arquivos e formatos.")
        return 1
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Política de runtime/CI válida; nenhum dos quatro padrões de segredo detectado.")
    print("Sem scan de CVEs, histórico, binários ou arquivos ignorados; não é certificação.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
