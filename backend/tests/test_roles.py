import pytest
from fastapi.testclient import TestClient

from app.filters.role_matching import match_title, remote_matches
from app.main import app

client = TestClient(app)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Desenvolvedor Backend", True),
        ("Analista Desenvolvedor", True),
        ("DESENVOLVEDOR JAVA", True),
        ("Pessoa Desenvolvedora Backend", True),
        ("Pessoa Desenvolvedor(a) Java", True),
        ("Desenvolvedor/a Python", True),
        ("Desenvolvedores Java", True),
        ("Desenvolvedoras Backend", True),
        ("Dev Frontend", True),
        ("DevOps Engineer", False),
        ("Software Developer", True),
        ("Analista de Suporte", False),
    ],
)
def test_matching_whole_words_in_titles(title, expected):
    assert bool(match_title(title, "Desenvolvedor", ["Dev", "Developer"])) is expected


def test_phrases_normalization_and_no_hidden_synonyms():
    assert match_title("JÚNIOR FULL-STACK Developer", "Full Stack", [])
    assert not match_title("Fullstack Developer", "Full Stack", [])
    assert not match_title("Engenheiro Civil de Software", "Engenheiro de Software", [])
    assert not match_title("JavaScript Developer", "Java", [])
    assert match_title("Desenvolvedor C++", "C++", [])
    assert not match_title("Desenvolvedor C#", "C++", [])


def test_remote_is_separate_and_unknown_is_excluded():
    assert remote_matches("Remoto")
    assert remote_matches("Remote")
    for value in [None, "Híbrido", "Presencial", "remoto ou híbrido", "onsite", "não informado"]:
        assert not remote_matches(value)


def test_broad_variations_and_specific_roles_remain_distinct():
    assert match_title("Pessoa Desenvolvedora Backend", "Desenvolvedor Backend", [])
    assert match_title("Backend Engineer", "Desenvolvedor Backend", ["Backend"]) == ["Backend"]
    assert match_title("Analista Backend Pleno", "Desenvolvedor Backend", ["Backend"])
    assert not match_title("Pessoa Desenvolvedora Frontend", "Desenvolvedor Backend", ["Backend"])
    assert not match_title("Backendless Developer", "Backend", [])
    assert not match_title("DevOps Engineer", "Dev", [])
    assert not match_title("JavaScript Developer", "Java", [])
    assert match_title("Desenvolvedor C++", "C++", [])
    assert not match_title("Desenvolvedor C#", "C++", [])


def test_crud_variations_selection_and_preview():
    created = client.post(
        "/api/roles",
        json={"nome": "Desenvolvedor", "variacoes": ["Dev", "dev", "Developer", "DESENVOLVEDOR"]},
    )
    assert created.status_code == 201
    role = created.json()
    assert role["variacoes"] == ["Dev", "Developer"]
    assert client.get("/api/roles").json()[0]["id"] == role["id"]
    preview = client.post("/api/roles/preview", json={"titulo": "Dev Backend"})
    assert preview.json()["cargos"][0]["termos"] == ["Dev"]
    assert (
        client.post("/api/roles/preview", json={"titulo": "DevOps"}).json()["corresponde"] is False
    )
    assert (
        client.patch(f"/api/roles/{role['id']}/selection", json={"selecionado": False}).json()[
            "selecionado"
        ]
        is False
    )
    assert not client.post("/api/roles/preview", json={"titulo": "Dev Backend"}).json()[
        "corresponde"
    ]
    updated = client.patch(
        f"/api/roles/{role['id']}",
        json={"nome": "Desenvolvedor Web", "variacoes": ["Dev Web"], "selecionado": True},
    )
    assert updated.json()["id"] == role["id"]
    assert client.delete(f"/api/roles/{role['id']}").status_code == 200
    assert client.get("/api/roles").json() == []
    assert client.delete(f"/api/roles/{role['id']}").status_code == 404


def test_duplicates_and_invalid_fields():
    assert client.post("/api/roles", json={"nome": "Engenharia de SofTware"}).status_code == 201
    assert client.post("/api/roles", json={"nome": " engenharia de software "}).status_code == 409
    for data in [
        {"nome": "---"},
        {"nome": ""},
        {"nome": "Dev", "variacoes": [" "]},
        {"nome": "Dev", "variacoes": ["x"] * 31},
    ]:
        assert client.post("/api/roles", json=data).status_code == 422
    assert len(client.get("/api/roles").json()) == 1


def test_preview_does_not_use_description():
    client.post("/api/roles", json={"nome": "Desenvolvedor"})
    assert (
        client.post(
            "/api/roles/preview", json={"titulo": "Suporte", "descricao": "Desenvolvedor"}
        ).status_code
        == 422
    )
