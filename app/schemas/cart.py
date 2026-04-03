from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CartItemAdd(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=9999)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=9999)


class CartLineRead(BaseModel):
    id: int
    product_id: int
    name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class CartRead(BaseModel):
    items: list[CartLineRead]
    item_count: int
    subtotal: Decimal
