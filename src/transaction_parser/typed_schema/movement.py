from __future__ import annotations

from ..field_descriptions import AMOUNTS, NET_QUANTITY, PRICE, PRICE_CURRENCY
from .base import SchemaModel, schema_field
from .instrument import Instrument as InstrumentModel
from .movement_amount import MovementAmount as MovementAmountModel


class Movement(SchemaModel):
    """A single flow of value, either security-side or cash-side."""

    Instrument: InstrumentModel = schema_field(
        description="Instrument that actually moves in this flow.",
    )
    NetQuantity: float = schema_field(
        description=NET_QUANTITY,
    )
    Price: float | None = schema_field(
        description=PRICE,
        default=None,
    )
    PriceCurrency: str | None = schema_field(
        description=PRICE_CURRENCY,
        default=None,
    )
    Amounts: list[MovementAmountModel] = schema_field(
        description=AMOUNTS,
        default_factory=list,
    )
