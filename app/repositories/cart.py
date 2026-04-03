from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.cart_item import CartItem
from app.models.product import Product


class CartRepository:
    @staticmethod
    async def get_line_by_user_product(
        db: AsyncSession, user_id: int, product_id: int
    ) -> Optional[CartItem]:
        result = await db.execute(
            select(CartItem).where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_line_by_id_for_user(
        db: AsyncSession, cart_item_id: int, user_id: int
    ) -> Optional[CartItem]:
        result = await db.execute(
            select(CartItem).where(
                CartItem.id == cart_item_id,
                CartItem.user_id == user_id,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def list_lines_with_products(db: AsyncSession, user_id: int) -> list[tuple[CartItem, Product]]:
        result = await db.execute(
            select(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.id)
        )
        return list(result.all())

    @staticmethod
    async def create(db: AsyncSession, user_id: int, product_id: int, quantity: int) -> CartItem:
        row = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row

    @staticmethod
    async def update_quantity(db: AsyncSession, line: CartItem, quantity: int) -> CartItem:
        line.quantity = quantity
        await db.commit()
        await db.refresh(line)
        return line

    @staticmethod
    async def delete(db: AsyncSession, line: CartItem) -> None:
        await db.delete(line)
        await db.commit()

    @staticmethod
    async def clear_user_cart(db: AsyncSession, user_id: int) -> None:
        await db.execute(delete(CartItem).where(CartItem.user_id == user_id))
        await db.commit()
