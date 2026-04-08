from __future__ import annotations

from ..field_descriptions import AMOUNT_CURRENCY, AMOUNT_DESCRIPTION, AMOUNT_QUANTITY, AMOUNT_STANDARDIZED_CODE
from .base import SchemaModel, schema_field
from .enums import MovementAmountStandardizedCode as MovementAmountStandardizedCodeEnum


class MovementAmount(SchemaModel):
    """Breakdown component of a cash movement."""

    AmountDescription: str = schema_field(
        description=AMOUNT_DESCRIPTION,
    )
    StandardizedCode: MovementAmountStandardizedCodeEnum = schema_field(
        description=AMOUNT_STANDARDIZED_CODE,
    )
    Quantity: float = schema_field(
        description=AMOUNT_QUANTITY,
    )
    Currency: str = schema_field(
        description=AMOUNT_CURRENCY,
    )
