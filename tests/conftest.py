import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Устанавливаем тестовые переменные окружения ДО импорта app
os.environ.setdefault("CLAUDE_API_KEY", "test-key")
os.environ.setdefault("FMP_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.infrastructure.database import Base
from app.dependencies import get_db
from app.main import app

# In-memory SQLite для тестов
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# JWT токен Investlink (декодируем без верификации)
# payload: {"user_id": "user-test-123", "sub": "user-test-123"}
FAKE_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJ1c2VyX2lkIjoidXNlci10ZXN0LTEyMyIsInN1YiI6InVzZXItdGVzdC0xMjMifQ"
    ".signature_not_verified"
)

AUTH_HEADERS = {"Authorization": f"Bearer {FAKE_TOKEN}"}
USER_ID = "user-test-123"
