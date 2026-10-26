import re
import unicodedata


def normalize_term(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = "".join(
        character if character.isalnum() or character in "+#" else " " for character in value
    )
    return " ".join(value.split())


def match_title(title: str, name: str, variations: list[str]) -> list[str]:
    normalized_title = f" {normalize_term(title)} "
    matched, seen = [], set()
    for term in [name, *variations]:
        normalized = normalize_term(term)
        if normalized and normalized not in seen and f" {normalized} " in normalized_title:
            matched.append(term)
            seen.add(normalized)
    return matched


def remote_matches(modality: str | None) -> bool:
    # Exige evidência estruturada; país/localidade não são inferidos aqui.
    value = normalize_term(modality or "")
    if re.search(r"\b(hibrido|hybrid|presencial|onsite)\b", value) or "on site" in value:
        return False
    return value in {"remoto", "remota", "remote", "fully remote", "100 remoto", "100 remote"}
