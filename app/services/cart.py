from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cart import CartRepository
from app.repositories.product import ProductRepository
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartLineRead, CartRead


class CartService:
    @staticmethod
    async def get_cart(db: AsyncSession, user_id: int) -> CartRead:
        rows = await CartRepository.list_lines_with_products(db, user_id)
        lines: list[CartLineRead] = []
        subtotal = Decimal("0")
        item_count = 0
        for cart_item, product in rows:
            unit = Decimal(str(product.price))
            qty = cart_item.quantity
            line_total = unit * qty
            subtotal += line_total
            item_count += qty
            lines.append(
                CartLineRead(
                    id=cart_item.id,
                    product_id=product.id,
                    name=product.name,
                    unit_price=unit,
                    quantity=qty,
                    line_total=line_total,
                )
            )
        return CartRead(items=lines, item_count=item_count, subtotal=subtotal)

    @staticmethod
    async def add_item(db: AsyncSession, user_id: int, payload: CartItemAdd) -> CartRead:
        product = await ProductRepository.get_by_id(db, payload.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        existing = await CartRepository.get_line_by_user_product(db, user_id, payload.product_id)
        new_qty = payload.quantity + (existing.quantity if existing else 0)
        if new_qty > product.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough stock for requested quantity",
            )

        if existing:
            await CartRepository.update_quantity(db, existing, new_qty)
        else:
            await CartRepository.create(db, user_id, payload.product_id, payload.quantity)

        return await CartService.get_cart(db, user_id)

    @staticmethod
    async def update_line(
        db: AsyncSession, user_id: int, cart_item_id: int, payload: CartItemUpdate
    ) -> CartRead:
        line = await CartRepository.get_line_by_id_for_user(db, cart_item_id, user_id)
        if not line:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

        product = await ProductRepository.get_by_id(db, line.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        if payload.quantity > product.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough stock for requested quantity",
            )

        await CartRepository.update_quantity(db, line, payload.quantity)
        return await CartService.get_cart(db, user_id)

    @staticmethod
    async def remove_line(db: AsyncSession, user_id: int, cart_item_id: int) -> CartRead:
        line = await CartRepository.get_line_by_id_for_user(db, cart_item_id, user_id)
        if not line:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
        await CartRepository.delete(db, line)
        return await CartService.get_cart(db, user_id)

    @staticmethod
    async def clear_cart(db: AsyncSession, user_id: int) -> CartRead:
        await CartRepository.clear_user_cart(db, user_id)
        return await CartService.get_cart(db, user_id)
