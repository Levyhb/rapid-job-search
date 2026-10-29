import time

from sqlalchemy import JSON, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PortalValidation(Base):
    __tablename__ = "portal_validations"
    company_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(String(2048))
    request_token: Mapped[str] = mapped_column(String(36))
    state: Mapped[str] = mapped_column(String(20))
    requested_at: Mapped[float] = mapped_column(Float, default=time.time)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
