from decimal import Decimal
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductRepository:
    @staticmethod
    async def create(db: AsyncSession, payload: ProductCreate) -> Product:
        product = Product(**payload.model_dump())
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalars().first()

    @staticmethod
    async def list(
        db: AsyncSession,
        category: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
    ) -> list[Product]:
        query: Select[tuple[Product]] = select(Product)
        if category:
            query = query.where(Product.category == category)
        if min_price is not None:
            query = query.where(Product.price >= min_price)
        if max_price is not None:
            query = query.where(Product.price <= max_price)
        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))

        result = await db.execute(query.order_by(Product.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def update(db: AsyncSession, product: Product, payload: ProductUpdate) -> Product:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def delete(db: AsyncSession, product: Product) -> None:
        await db.delete(product)
        await db.commit()
