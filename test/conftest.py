import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

TEST_DB_FILE = "test.db"
TEST_DB_URL = f"sqlite:///./{TEST_DB_FILE}"


@pytest.fixture()
def client():
    # Crée une DB de test
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Recrée les tables à chaque test (propre)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Override de la dépendance get_db pour utiliser la DB de test
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Client FastAPI
    with TestClient(app) as c:
        yield c

    # Nettoyage : enlève l'override + ferme l'engine (IMPORTANT Windows)
    app.dependency_overrides.clear()
    engine.dispose()

    # Supprime le fichier DB de test
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
