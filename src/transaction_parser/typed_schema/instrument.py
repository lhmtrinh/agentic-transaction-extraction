from __future__ import annotations

from ..field_descriptions import INSTRUMENT_NAME, INSTRUMENT_REFERENCES, INSTRUMENT_TYPE, QUOTE_TYPE
from .base import SchemaModel, schema_field
from .enums import InstrumentType as InstrumentTypeEnum, QuoteType as QuoteTypeEnum
from .instrument_reference import InstrumentReference


class Instrument(SchemaModel):
    """Security or account involved in a movement or referenced as transaction context."""

    Type: InstrumentTypeEnum = schema_field(
        description=INSTRUMENT_TYPE,
    )
    Name: str = schema_field(
        description=INSTRUMENT_NAME,
    )
    QuoteType: QuoteTypeEnum | None = schema_field(
        description=QUOTE_TYPE,
        default=None,
    )
    References: list[InstrumentReference] = schema_field(
        description=INSTRUMENT_REFERENCES,
        default_factory=list,
    )
