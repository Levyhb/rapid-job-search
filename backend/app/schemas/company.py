from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class CompanyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nome: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        try:
            AnyHttpUrl(value)
            parsed = urlsplit(value)
            valid = (
                parsed.scheme in {"http", "https"}
                and parsed.hostname
                and not parsed.username
                and not parsed.password
                and not any(character.isspace() for character in value)
                and "\\" not in value
            )
            _ = parsed.port
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Informe um link HTTP ou HTTPS válido, sem credenciais ou espaços.")
        return value


class Company(CompanyInput):
    id: str = Field(min_length=1)


class CompanyBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    empresas: list[CompanyInput] = Field(min_length=1, max_length=10000)


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    versao: Literal[1] = 1
    empresas: list[Company] = Field(default_factory=list, max_length=10000)


class ImportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    versao: Literal[1]
    empresas: list[Any] = Field(max_length=10000)
