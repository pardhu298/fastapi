import asyncio
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.base import Base
from app.models.user import User
from app.repositories.user import UserRepository
import hashlib
from app.services import auth as auth_service
import app.api.v1.endpoints.auth as auth_endpoints

pytestmark = pytest.mark.unit

# Setup sync in-memory SQLite for tests
SYNC_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SyncSession = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# Helpers to run sync DB ops in thread pool
async def run_sync(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

# Sync DB operations
def sync_get_by_id(user_id: int):
    with SyncSession() as s:
        return s.query(User).filter_by(id=user_id).first()


def sync_get_by_email(email: str):
    with SyncSession() as s:
        return s.query(User).filter_by(email=email).first()

def sync_create_user(email: str, hashed_password: str):
    with SyncSession() as s:
        user = User(email=email, hashed_password=hashed_password)
        s.add(user)
        s.commit()
        s.refresh(user)
        return user


def sync_promote_user(email: str):
    with SyncSession() as s:
        user = s.query(User).filter_by(email=email).first()
        user.is_superuser = True
        s.commit()

# Async wrappers to monkeypatch repository methods
async def async_get_by_id(_db, user_id: int):
    return await run_sync(sync_get_by_id, user_id)


async def async_get_by_email(_db, email: str):
    return await run_sync(sync_get_by_email, email)

async def async_create(_db, user_in, hashed_password: str):
    user = await run_sync(sync_create_user, user_in.email, hashed_password)
    return user

@pytest.fixture(autouse=True)
def patch_user_repo(monkeypatch):
    # Monkeypatch the async repository methods to use the sync SQLite test DB
    monkeypatch.setattr(UserRepository, "get_by_id", staticmethod(async_get_by_id))
    monkeypatch.setattr(UserRepository, "get_by_email", staticmethod(async_get_by_email))
    monkeypatch.setattr(UserRepository, "create", staticmethod(async_create))
    # Replace password hashing/verification with fast deterministic test implementations
    def fake_hash(password: str) -> str:
        return "sha256$" + hashlib.sha256(password.encode()).hexdigest()

    def fake_verify(plain: str, hashed: str) -> bool:
        if not hashed.startswith("sha256$"):
            return False
        return hashlib.sha256(plain.encode()).hexdigest() == hashed.split("$", 1)[1]

    monkeypatch.setattr(auth_service, "hash_password", fake_hash)
    monkeypatch.setattr(auth_service, "verify_password", fake_verify)
    # Also patch the references imported into the endpoint module
    monkeypatch.setattr(auth_endpoints, "hash_password", fake_hash)
    monkeypatch.setattr(auth_endpoints, "verify_password", fake_verify)
    yield


def test_register_login_flow():
    # Register
    resp = client.post("/api/v1/auth/register", json={"email": "syncuser@example.com", "password": "SyncPass123"})
    assert resp.status_code == 201

    # Duplicate registration
    resp2 = client.post("/api/v1/auth/register", json={"email": "syncuser@example.com", "password": "SyncPass123"})
    assert resp2.status_code == 400

    # Login success
    resp3 = client.post("/api/v1/auth/login", json={"email": "syncuser@example.com", "password": "SyncPass123"})
    assert resp3.status_code == 200
    data = resp3.json()
    assert "access_token" in data and "refresh_token" in data

    # Refresh token flow
    resp_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert resp_refresh.status_code == 200
    refreshed = resp_refresh.json()
    assert "access_token" in refreshed and "refresh_token" in refreshed

    # Invalid password
    resp4 = client.post("/api/v1/auth/login", json={"email": "syncuser@example.com", "password": "WrongPass"})
    assert resp4.status_code == 401

    # Nonexistent user
    resp5 = client.post("/api/v1/auth/login", json={"email": "nosuch@example.com", "password": "AnyPass"})
    assert resp5.status_code == 401


def test_register_returns_500_when_hashing_backend_fails(monkeypatch):
    def failing_hash(_password: str) -> str:
        raise ValueError("hash backend failure")

    monkeypatch.setattr(auth_endpoints, "hash_password", failing_hash)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "hashfail@example.com", "password": "StrongPass123"},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Password hashing failed due to server configuration"


def test_auth_me_and_admin_access_flow():
    register_email = "roleuser@example.com"
    password = "RolePass123"

    register = client.post(
        "/api/v1/auth/register",
        json={"email": register_email, "password": password},
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": register_email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == register_email

    forbidden = client.get("/api/v1/auth/admin/dashboard", headers=headers)
    assert forbidden.status_code == 403

    sync_promote_user(register_email)
    allowed = client.get("/api/v1/auth/admin/dashboard", headers=headers)
    assert allowed.status_code == 200
    assert allowed.json()["message"] == "Welcome, admin"
