from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user, get_db
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartRead
from app.services.cart import CartService

router = APIRouter(prefix="/cart")


@router.get("", response_model=CartRead)
async def get_my_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CartService.get_cart(db, current_user.id)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_200_OK)
async def add_cart_item(
    payload: CartItemAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CartService.add_item(db, current_user.id, payload)


@router.patch("/items/{cart_item_id}", response_model=CartRead)
async def update_cart_item(
    cart_item_id: int,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CartService.update_line(db, current_user.id, cart_item_id, payload)


@router.delete("/items/{cart_item_id}", response_model=CartRead)
async def delete_cart_item(
    cart_item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CartService.remove_line(db, current_user.id, cart_item_id)


@router.delete("", response_model=CartRead)
async def clear_my_cart(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await CartService.clear_cart(db, current_user.id)
