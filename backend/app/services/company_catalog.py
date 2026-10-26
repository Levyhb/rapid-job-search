import logging
import os
import tempfile
import threading
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.company import Catalog, Company, CompanyInput, ImportDocument

logger = logging.getLogger(__name__)
_thread_lock = threading.RLock()


class CatalogError(Exception):
    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def signature(company: CompanyInput) -> tuple[str, str]:
    name = " ".join(
        "".join(
            character
            for character in unicodedata.normalize("NFKD", company.nome)
            if not unicodedata.combining(character)
        )
        .casefold()
        .split()
    )
    parts = urlsplit(company.url)
    # Preservar query e caminho: podem identificar o portal da empresa.
    url = urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, parts.fragment)
    )
    return name, url


class CompanyCatalog:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _locked(self):
        with _thread_lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.with_suffix(self.path.suffix + ".lock").open("a+b") as lock:
                    if lock.tell() == 0:
                        lock.write(b"0")
                        lock.flush()
                    lock.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        lock.seek(0)
                        if os.name == "nt":
                            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except OSError as error:
                logger.exception("Falha de acesso ao catálogo de empresas")
                raise CatalogError(
                    "Não foi possível acessar o cadastro. Tente novamente."
                ) from error

    def _read(self) -> Catalog:
        if not self.path.exists():
            return Catalog()
        try:
            catalog = Catalog.model_validate_json(self.path.read_text(encoding="utf-8-sig"))
            ids = [company.id for company in catalog.empresas]
            if len(ids) != len(set(ids)):
                raise ValueError("IDs repetidos")
            return catalog
        except (ValidationError, ValueError) as error:
            logger.exception("Catálogo inválido; arquivo preservado")
            raise CatalogError(
                "O arquivo de empresas está inválido. Corrija ou restaure o arquivo no servidor; "
                "os dados foram preservados."
            ) from error

    def _write(self, catalog: Catalog):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, suffix=".tmp", delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(catalog.model_dump_json(indent=2) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()

    def list(self) -> list[Company]:
        with self._locked():
            return self._read().empresas

    def save(self, data: CompanyInput, company_id: str | None = None) -> Company:
        with self._locked():
            catalog = self._read()
            if company_id and not any(item.id == company_id for item in catalog.empresas):
                raise CatalogError("Empresa não encontrada. Atualize a lista.", 404)
            if any(
                item.id != company_id and signature(item) == signature(data)
                for item in catalog.empresas
            ):
                raise CatalogError("Esta empresa com esse link já está cadastrada.", 409)
            if not company_id and len(catalog.empresas) >= 10000:
                raise CatalogError("O cadastro atingiu o limite de 10.000 empresas.", 422)
            company = Company(id=company_id or str(uuid4()), **data.model_dump())
            if company_id:
                catalog.empresas = [
                    company if item.id == company_id else item for item in catalog.empresas
                ]
            else:
                catalog.empresas.append(company)
            self._write(catalog)
            return company

    def remove(self, company_id: str):
        with self._locked():
            catalog = self._read()
            remaining = [item for item in catalog.empresas if item.id != company_id]
            if len(remaining) == len(catalog.empresas):
                raise CatalogError("Empresa não encontrada. Atualize a lista.", 404)
            catalog.empresas = remaining
            self._write(catalog)

    def export(self) -> dict:
        return {"versao": 1, "empresas": [item.model_dump(exclude={"id"}) for item in self.list()]}

    @staticmethod
    def _preview(document: ImportDocument, existing: list[Company]) -> dict:
        seen = {signature(item) for item in existing}
        valid, errors, duplicates = [], [], 0
        for index, row in enumerate(document.empresas, 1):
            try:
                # IDs de outra instalação não fazem parte da identidade local.
                data = (
                    {key: value for key, value in row.items() if key != "id"}
                    if isinstance(row, dict)
                    else row
                )
                company = CompanyInput.model_validate(data)
            except ValidationError as error:
                errors.append(
                    {"linha": index, "motivo": "; ".join(item["msg"] for item in error.errors())}
                )
                continue
            key = signature(company)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            valid.append(company.model_dump())
        return {"empresas": valid, "erros": errors, "duplicadas": duplicates}

    def preview(self, document: ImportDocument) -> dict:
        with self._locked():
            return self._preview(document, self._read().empresas)

    def import_document(self, document: ImportDocument) -> dict:
        with self._locked():
            catalog = self._read()
            preview = self._preview(document, catalog.empresas)
            if preview["erros"]:
                raise CatalogError(
                    "O JSON contém empresas inválidas. Revise antes de importar.", 422
                )
            if len(catalog.empresas) + len(preview["empresas"]) > 10000:
                raise CatalogError("A importação excede o limite de 10.000 empresas.", 422)
            catalog.empresas.extend(Company(id=str(uuid4()), **row) for row in preview["empresas"])
            if preview["empresas"]:
                self._write(catalog)
            return {"importadas": len(preview["empresas"]), "duplicadas": preview["duplicadas"]}
