from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.filters.role_matching import normalize_term


class RoleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nome: str = Field(min_length=1, max_length=120)
    variacoes: list[str] = Field(default_factory=list, max_length=30)
    selecionado: bool = True

    @field_validator("nome")
    @classmethod
    def valid_name(cls, value):
        if not any(character.isalnum() for character in value):
            raise ValueError("O cargo deve conter letras ou números.")
        return value

    @field_validator("variacoes")
    @classmethod
    def valid_variations(cls, values):
        cleaned = []
        for value in values:
            value = value.strip()
            if not value or len(value) > 120 or not any(character.isalnum() for character in value):
                raise ValueError(
                    "Cada variação deve conter de 1 a 120 caracteres com letras ou números."
                )
            cleaned.append(value)
        return cleaned

    @model_validator(mode="after")
    def deduplicate_variations(self):
        seen = {normalize_term(self.nome)}
        unique = []
        for value in self.variacoes:
            normalized = normalize_term(value)
            if normalized not in seen:
                unique.append(value)
                seen.add(normalized)
        self.variacoes = unique
        return self


class RoleOutput(RoleInput):
    model_config = ConfigDict(from_attributes=True)
    id: str


class RoleSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selecionado: bool


class TitlePreview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    titulo: str = Field(min_length=1, max_length=500)
