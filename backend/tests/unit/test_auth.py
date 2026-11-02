from datetime import timedelta

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.models.user import User, UserRole
from app.main import app

# In-memory SQLite DB for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def test_db():
    # SEED_PASSWORD is the source of truth for the dev/test seed password.
    test_password = settings.SEED_PASSWORD or "test-password"
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    hashed = get_password_hash(test_password)
    users = [
        User(
            name="Chairman",
            username="chairman",
            email="chairman@university.com",
            role=UserRole.CHAIRMAN,
            hashed_password=hashed,
        ),
        User(
            name="Principal",
            username="principal",
            email="principal@university.com",
            role=UserRole.PRINCIPAL,
            hashed_password=hashed,
        ),
        User(
            name="HOD",
            username="hod",
            email="hod@university.com",
            role=UserRole.HOD,
            hashed_password=hashed,
        ),
        User(
            name="Teacher",
            username="teacher",
            email="teacher@university.com",
            role=UserRole.TEACHER,
            hashed_password=hashed,
        ),
        User(name="Aniket", username="aniket", email="aniket@university.com", role=UserRole.STUDENT, hashed_password=hashed),
        User(name="Sujal", username="sujal", email="sujal@university.com", role=UserRole.STUDENT, hashed_password=hashed),
        User(name="Viraj", username="viraj", email="viraj@university.com", role=UserRole.STUDENT, hashed_password=hashed),
        User(name="Sarvesh", username="sarvesh", email="sarvesh@university.com", role=UserRole.STUDENT, hashed_password=hashed),
    ]
    db.add_all(users)
    db.commit()
    yield db, test_password
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(test_db):
    db, _ = test_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_login_success_with_username(client, test_db):
    _, password = test_db
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman", "password": password},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "chairman"
    assert data["user"]["role"] == "chairman"


def test_login_success_with_email(client, test_db):
    _, password = test_db
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman@university.com", "password": password},
    )
    assert res.status_code == 200


def test_dev_login_success(client, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    res = client.post("/api/v1/auth/dev/login", json={"username": "chairman"})

    assert res.status_code == 200
    token = res.json()["access_token"]
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "chairman"


def test_dev_login_disabled_outside_development(client, monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    res = client.post("/api/v1/auth/dev/login", json={"username": "chairman"})

    assert res.status_code == 404


def test_login_wrong_password(client, test_db):
    _, password = test_db
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman", "password": "wrong-" + password},
    )
    assert res.status_code == 401


def test_login_unknown_user(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "whatever"},
    )
    assert res.status_code == 401


def test_invalid_and_expired_tokens_return_401(client):
    invalid = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    expired_token = create_access_token(
        subject="1",
        expires_delta=timedelta(seconds=-1),
    )
    expired = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert invalid.status_code == 401
    assert expired.status_code == 401


def test_login_database_unavailable_returns_503(client, monkeypatch):
    def unavailable_db() -> None:
        raise OperationalError("SELECT ...", {}, OSError("database unavailable"))

    monkeypatch.setitem(app.dependency_overrides, get_db, unavailable_db)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman", "password": "any-password"},
    )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "2"
    assert response.json()["detail"] == "Database temporarily unavailable. Please try again."


def test_ready_does_not_query_database(client, monkeypatch):
    def database_probe_is_not_allowed():
        raise AssertionError("readiness must not access the database")

    monkeypatch.setattr("app.db.session.SessionLocal", database_probe_is_not_allowed)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_role_access(client, test_db):
    _, password = test_db
    # Login as chairman
    res_admin = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman", "password": password},
    )
    admin_token = res_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Chairman access chairman-only endpoint
    res = client.get("/api/v1/auth/chairman-only", headers=admin_headers)
    assert res.status_code == 200
    assert "Welcome Chairman" in res.json()["message"]

    # Login as student
    res_att = client.post(
        "/api/v1/auth/login",
        json={"username": "aniket@university.com", "password": password},
    )
    att_token = res_att.json()["access_token"]
    att_headers = {"Authorization": f"Bearer {att_token}"}

    # Student tries chairman-only endpoint -> 403 Forbidden
    res_forbidden = client.get("/api/v1/auth/chairman-only", headers=att_headers)
    assert res_forbidden.status_code == 403


@pytest.mark.parametrize(
    ("username", "role"),
    [
        ("chairman", "chairman"),
        ("principal", "principal"),
        ("hod", "hod"),
        ("teacher", "teacher"),
        ("aniket", "student"),
        ("sujal", "student"),
        ("viraj", "student"),
        ("sarvesh", "student"),
    ],
)
def test_each_university_user_authenticates_with_expected_role(client, test_db, username, role):
    _, password = test_db
    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200
    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["role"] == role


def test_me_returns_username(client, test_db):
    _, password = test_db
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "principal", "password": password},
    )
    token = res.json()["access_token"]
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "principal"
    assert body["email"] == "principal@university.com"