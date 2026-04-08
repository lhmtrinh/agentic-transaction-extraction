from __future__ import annotations

from ..field_descriptions import REFERENCE_KEY, REFERENCE_VALUE
from .base import SchemaModel, schema_field


class InstrumentReference(SchemaModel):
    """Reference identifier for a security or account."""

    Key: str = schema_field(
        description=REFERENCE_KEY,
        examples=["ISIN", "Valor", "WKN", "IBAN", "AccountNumber"],
    )
    Value: str = schema_field(
        description=REFERENCE_VALUE,
    )
