import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy import select
from uuid import uuid4

from app.db.session import AsyncSessionLocal
from app.db.session import engine
from app.main import app
from app.models.base import Base
from app.models.user import User


@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_db():
    """Ensure tables exist for integration test execution."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def post_json(client: AsyncClient, url: str, json_data: dict):
    return await client.post(url, json=json_data)


async def test_register_and_login_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        test_email = f"testuser-{uuid4().hex}@example.com"

        resp = await post_json(
            ac,
            "/api/v1/auth/register",
            {"email": test_email, "password": "TestPass123"},
        )
        assert resp.status_code == 201

        resp2 = await post_json(
            ac,
            "/api/v1/auth/register",
            {"email": test_email, "password": "TestPass123"},
        )
        assert resp2.status_code == 400

        resp3 = await post_json(
            ac,
            "/api/v1/auth/login",
            {"email": test_email, "password": "TestPass123"},
        )
        assert resp3.status_code == 200
        data = resp3.json()
        assert "access_token" in data and "refresh_token" in data
        headers = {"Authorization": f"Bearer {data['access_token']}"}

        me_resp = await ac.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == test_email

        admin_forbidden = await ac.get("/api/v1/auth/admin/dashboard", headers=headers)
        assert admin_forbidden.status_code == 403

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == test_email))
            user = result.scalars().first()
            user.is_superuser = True
            await db.commit()

        admin_allowed = await ac.get("/api/v1/auth/admin/dashboard", headers=headers)
        assert admin_allowed.status_code == 200
        assert admin_allowed.json()["message"] == "Welcome, admin"

        resp_refresh = await post_json(
            ac,
            "/api/v1/auth/refresh",
            {"refresh_token": data["refresh_token"]},
        )
        assert resp_refresh.status_code == 200
        refreshed = resp_refresh.json()
        assert "access_token" in refreshed and "refresh_token" in refreshed

        resp4 = await post_json(
            ac,
            "/api/v1/auth/login",
            {"email": test_email, "password": "WrongPass"},
        )
        assert resp4.status_code == 401

        resp5 = await post_json(
            ac,
            "/api/v1/auth/login",
            {"email": "nouser@example.com", "password": "AnyPass"},
        )
        assert resp5.status_code == 401
