from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    @staticmethod
    async def create_product(db: AsyncSession, payload: ProductCreate):
        return await ProductRepository.create(db, payload)

    @staticmethod
    async def list_products(
        db: AsyncSession,
        category: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
    ):
        return await ProductRepository.list(db, category, min_price, max_price, search)

    @staticmethod
    async def get_product_or_404(db: AsyncSession, product_id: int):
        product = await ProductRepository.get_by_id(db, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return product

    @staticmethod
    async def update_product(db: AsyncSession, product_id: int, payload: ProductUpdate):
        product = await ProductService.get_product_or_404(db, product_id)
        return await ProductRepository.update(db, product, payload)

    @staticmethod
    async def delete_product(db: AsyncSession, product_id: int):
        product = await ProductService.get_product_or_404(db, product_id)
        await ProductRepository.delete(db, product)
