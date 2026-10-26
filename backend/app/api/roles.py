from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.filters.role_matching import match_title
from app.models.role import Role
from app.schemas.role import RoleInput, RoleOutput, RoleSelection, TitlePreview
from app.services.roles import commit_role, get_role, save_role

router = APIRouter(prefix="/api/roles", tags=["Cargos"])


@router.get("", response_model=list[RoleOutput])
def list_roles(session: Session = Depends(get_session)):
    return session.scalars(select(Role).order_by(Role.normalized_name, Role.id)).all()


@router.post("", response_model=RoleOutput, status_code=201)
def add_role(data: RoleInput, session: Session = Depends(get_session)):
    return save_role(session, data)


@router.post("/preview")
def preview_title(data: TitlePreview, session: Session = Depends(get_session)):
    matches = []
    for role in session.scalars(
        select(Role).where(Role.selecionado.is_(True)).order_by(Role.normalized_name)
    ):
        terms = match_title(data.titulo, role.nome, role.variacoes)
        if terms:
            matches.append({"id": role.id, "nome": role.nome, "termos": terms})
    return {"corresponde": bool(matches), "cargos": matches, "escopo": "titulo"}


@router.patch("/{role_id}", response_model=RoleOutput)
def edit_role(role_id: str, data: RoleInput, session: Session = Depends(get_session)):
    return save_role(session, data, role_id)


@router.patch("/{role_id}/selection", response_model=RoleOutput)
def select_role(role_id: str, data: RoleSelection, session: Session = Depends(get_session)):
    role = get_role(session, role_id)
    role.selecionado = data.selecionado
    return commit_role(session, role)


@router.delete("/{role_id}")
def remove_role(role_id: str, session: Session = Depends(get_session)):
    session.delete(get_role(session, role_id))
    session.commit()
    return {"removed": True}
