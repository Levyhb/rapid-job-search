from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.services.portal_validation import get_validation_service


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)

    def session_override():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_validation_service] = lambda: MagicMock()
    yield
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_validation_service, None)
    engine.dispose()
