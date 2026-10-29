from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.filters.role_matching import normalize_term
from app.models.role import Role
from app.schemas.role import RoleInput


def get_role(session: Session, role_id: str) -> Role:
    role = session.get(Role, role_id)
    if role is None:
        raise HTTPException(404, "Cargo não encontrado. Atualize a lista.")
    return role


def commit_role(session: Session, role: Role):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "Um cargo com esse nome já está cadastrado.") from None
    session.refresh(role)
    return role


def save_role(session: Session, data: RoleInput, role_id: str | None = None):
    role = get_role(session, role_id) if role_id else Role()
    if not role_id and session.scalar(select(func.count()).select_from(Role)) >= 1000:
        raise HTTPException(422, "O cadastro atingiu o limite de 1.000 cargos.")
    role.nome = data.nome
    role.normalized_name = normalize_term(data.nome)
    role.variacoes = data.variacoes
    role.selecionado = data.selecionado
    session.add(role)
    return commit_role(session, role)
