import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use a test sqlite database
os.environ["DATABASE_URL"] = "sqlite:///./test_doc_intelligence.db"

from app.core.database import Base, get_db
from app.main import app
from app.core.security import hash_password, create_access_token
from app.models.user import User

test_engine = create_engine("sqlite:///./test_doc_intelligence.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_doc_intelligence.db"):
        try:
            os.remove("./test_doc_intelligence.db")
        except Exception:
            pass

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_user(db_session):
    user = db_session.query(User).filter(User.email == "tester@pragatibharati.in").first()
    if not user:
        user = User(
            email="tester@pragatibharati.in",
            username="tester",
            hashed_password=hash_password("TestPassword123!")
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}
