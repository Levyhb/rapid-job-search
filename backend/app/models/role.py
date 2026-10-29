from uuid import uuid4

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    nome: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(240), unique=True)
    variacoes: Mapped[list[str]] = mapped_column(JSON, default=list)
    selecionado: Mapped[bool] = mapped_column(Boolean, default=True)
