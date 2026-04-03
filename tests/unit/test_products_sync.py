import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.models.product import Product
from app.models.user import User
from app.repositories.product import ProductRepository
from app.repositories.user import UserRepository
from app.services import auth as auth_service
import app.api.v1.endpoints.auth as auth_endpoints

pytestmark = pytest.mark.unit

SYNC_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SyncSession = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)


async def run_sync(fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


def sync_get_user_by_id(user_id: int):
    with SyncSession() as s:
        return s.query(User).filter_by(id=user_id).first()


def sync_get_user_by_email(email: str):
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


def sync_create_product(payload):
    with SyncSession() as s:
        product = Product(**payload.model_dump())
        s.add(product)
        s.commit()
        s.refresh(product)
        return product


def sync_get_product_by_id(product_id: int):
    with SyncSession() as s:
        return s.query(Product).filter_by(id=product_id).first()


def sync_list_products(category=None):
    with SyncSession() as s:
        q = s.query(Product)
        if category:
            q = q.filter_by(category=category)
        return q.all()


def sync_update_product(product_id: int, payload):
    with SyncSession() as s:
        product = s.query(Product).filter_by(id=product_id).first()
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        s.commit()
        s.refresh(product)
        return product


def sync_delete_product(product_id: int):
    with SyncSession() as s:
        product = s.query(Product).filter_by(id=product_id).first()
        s.delete(product)
        s.commit()


async def async_get_user_by_id(_db, user_id: int):
    return await run_sync(sync_get_user_by_id, user_id)


async def async_get_user_by_email(_db, email: str):
    return await run_sync(sync_get_user_by_email, email)


async def async_create_user(_db, user_in, hashed_password: str):
    return await run_sync(sync_create_user, user_in.email, hashed_password)


async def async_create_product(_db, payload):
    return await run_sync(sync_create_product, payload)


async def async_get_product_by_id(_db, product_id: int):
    return await run_sync(sync_get_product_by_id, product_id)


async def async_list_products(_db, category=None, min_price=None, max_price=None, search=None):
    products = await run_sync(sync_list_products, category)
    filtered = []
    for item in products:
        if min_price is not None and item.price < min_price:
            continue
        if max_price is not None and item.price > max_price:
            continue
        if search and search.lower() not in item.name.lower():
            continue
        filtered.append(item)
    return filtered


async def async_update_product(_db, product, payload):
    return await run_sync(sync_update_product, product.id, payload)


async def async_delete_product(_db, product):
    await run_sync(sync_delete_product, product.id)


@pytest.fixture(autouse=True)
def patch_repositories(monkeypatch):
    monkeypatch.setattr(UserRepository, "get_by_id", staticmethod(async_get_user_by_id))
    monkeypatch.setattr(UserRepository, "get_by_email", staticmethod(async_get_user_by_email))
    monkeypatch.setattr(UserRepository, "create", staticmethod(async_create_user))
    monkeypatch.setattr(ProductRepository, "create", staticmethod(async_create_product))
    monkeypatch.setattr(ProductRepository, "get_by_id", staticmethod(async_get_product_by_id))
    monkeypatch.setattr(ProductRepository, "list", staticmethod(async_list_products))
    monkeypatch.setattr(ProductRepository, "update", staticmethod(async_update_product))
    monkeypatch.setattr(ProductRepository, "delete", staticmethod(async_delete_product))

    def fake_hash(password: str) -> str:
        return "sha256$" + hashlib.sha256(password.encode()).hexdigest()

    def fake_verify(plain: str, hashed: str) -> bool:
        if not hashed.startswith("sha256$"):
            return False
        return hashlib.sha256(plain.encode()).hexdigest() == hashed.split("$", 1)[1]

    monkeypatch.setattr(auth_service, "hash_password", fake_hash)
    monkeypatch.setattr(auth_service, "verify_password", fake_verify)
    monkeypatch.setattr(auth_endpoints, "hash_password", fake_hash)
    monkeypatch.setattr(auth_endpoints, "verify_password", fake_verify)
    yield


def test_product_crud_and_filters():
    email = "product-admin@example.com"
    password = "ProductPass123"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    forbidden_create = client.post(
        "/api/v1/products",
        headers=headers,
        json={"name": "iPhone 16", "description": "Phone", "category": "mobiles", "price": 999.99, "stock": 10},
    )
    assert forbidden_create.status_code == 403

    sync_promote_user(email)

    created = client.post(
        "/api/v1/products",
        headers=headers,
        json={"name": "iPhone 16", "description": "Phone", "category": "mobiles", "price": 999.99, "stock": 10},
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    client.post(
        "/api/v1/products",
        headers=headers,
        json={"name": "MacBook Air", "description": "Laptop", "category": "laptops", "price": 1299.00, "stock": 5},
    )

    listed = client.get("/api/v1/products?category=mobiles")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    search_list = client.get("/api/v1/products?search=iphone")
    assert search_list.status_code == 200
    assert len(search_list.json()) == 1

    updated = client.put(
        f"/api/v1/products/{product_id}",
        headers=headers,
        json={"price": 949.99, "stock": 15},
    )
    assert updated.status_code == 200
    assert float(updated.json()["price"]) == 949.99
    assert updated.json()["stock"] == 15

    deleted = client.delete(f"/api/v1/products/{product_id}", headers=headers)
    assert deleted.status_code == 204
