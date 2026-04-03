import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.user import User
from app.repositories.cart import CartRepository
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


def sync_get_line_by_user_product(user_id: int, product_id: int):
    with SyncSession() as s:
        return s.query(CartItem).filter_by(user_id=user_id, product_id=product_id).first()


def sync_get_line_by_id_for_user(cart_item_id: int, user_id: int):
    with SyncSession() as s:
        return s.query(CartItem).filter_by(id=cart_item_id, user_id=user_id).first()


def sync_list_cart_with_products(user_id: int):
    with SyncSession() as s:
        return (
            s.query(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .filter(CartItem.user_id == user_id)
            .order_by(CartItem.id)
            .all()
        )


def sync_create_cart_line(user_id: int, product_id: int, quantity: int):
    with SyncSession() as s:
        row = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def sync_update_cart_quantity(line: CartItem, quantity: int):
    with SyncSession() as s:
        obj = s.query(CartItem).filter_by(id=line.id).first()
        obj.quantity = quantity
        s.commit()
        s.refresh(obj)
        return obj


def sync_delete_cart_line(line: CartItem):
    with SyncSession() as s:
        obj = s.query(CartItem).filter_by(id=line.id).first()
        if obj:
            s.delete(obj)
            s.commit()


def sync_clear_cart(user_id: int):
    with SyncSession() as s:
        s.query(CartItem).filter_by(user_id=user_id).delete()
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


async def async_get_line_by_user_product(_db, user_id: int, product_id: int):
    return await run_sync(sync_get_line_by_user_product, user_id, product_id)


async def async_get_line_by_id_for_user(_db, cart_item_id: int, user_id: int):
    return await run_sync(sync_get_line_by_id_for_user, cart_item_id, user_id)


async def async_list_lines_with_products(_db, user_id: int):
    return await run_sync(sync_list_cart_with_products, user_id)


async def async_create_cart(_db, user_id: int, product_id: int, quantity: int):
    return await run_sync(sync_create_cart_line, user_id, product_id, quantity)


async def async_update_cart_quantity(_db, line, quantity: int):
    return await run_sync(sync_update_cart_quantity, line, quantity)


async def async_delete_cart_line(_db, line):
    await run_sync(sync_delete_cart_line, line)


async def async_clear_user_cart(_db, user_id: int):
    await run_sync(sync_clear_cart, user_id)


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
    monkeypatch.setattr(CartRepository, "get_line_by_user_product", staticmethod(async_get_line_by_user_product))
    monkeypatch.setattr(CartRepository, "get_line_by_id_for_user", staticmethod(async_get_line_by_id_for_user))
    monkeypatch.setattr(CartRepository, "list_lines_with_products", staticmethod(async_list_lines_with_products))
    monkeypatch.setattr(CartRepository, "create", staticmethod(async_create_cart))
    monkeypatch.setattr(CartRepository, "update_quantity", staticmethod(async_update_cart_quantity))
    monkeypatch.setattr(CartRepository, "delete", staticmethod(async_delete_cart_line))
    monkeypatch.setattr(CartRepository, "clear_user_cart", staticmethod(async_clear_user_cart))

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


def _auth_headers(email: str, password: str):
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_product_as_admin(headers: dict, name: str, price: float, stock: int):
    sync_promote_user("cartuser@example.com")
    resp = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "name": name,
            "description": "d",
            "category": "cat",
            "price": price,
            "stock": stock,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_cart_add_merge_update_remove_clear():
    email = "cartuser@example.com"
    password = "CartPass123"
    headers = _auth_headers(email, password)
    pid = _create_product_as_admin(headers, "Widget", 10.0, 5)

    empty = client.get("/api/v1/cart", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["item_count"] == 0
    assert float(empty.json()["subtotal"]) == 0.0

    add1 = client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": pid, "quantity": 2},
    )
    assert add1.status_code == 200
    data1 = add1.json()
    assert data1["item_count"] == 2
    assert float(data1["subtotal"]) == 20.0

    add2 = client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": pid, "quantity": 1},
    )
    assert add2.status_code == 200
    assert add2.json()["item_count"] == 3

    line_id = add2.json()["items"][0]["id"]
    patch = client.patch(
        f"/api/v1/cart/items/{line_id}",
        headers=headers,
        json={"quantity": 4},
    )
    assert patch.status_code == 200
    assert patch.json()["item_count"] == 4

    rem = client.delete(f"/api/v1/cart/items/{line_id}", headers=headers)
    assert rem.status_code == 200
    assert rem.json()["item_count"] == 0

    client.post("/api/v1/cart/items", headers=headers, json={"product_id": pid, "quantity": 1})
    cleared = client.delete("/api/v1/cart", headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["item_count"] == 0


def test_cart_rejects_over_stock():
    email = "cartuser2@example.com"
    password = "CartPass123"
    headers = _auth_headers(email, password)
    sync_promote_user(email)
    created = client.post(
        "/api/v1/products",
        headers=headers,
        json={"name": "Limited", "description": "x", "category": "cat", "price": 1.0, "stock": 2},
    )
    pid = created.json()["id"]

    bad = client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": pid, "quantity": 5},
    )
    assert bad.status_code == 400
    assert "stock" in bad.json()["detail"].lower()
