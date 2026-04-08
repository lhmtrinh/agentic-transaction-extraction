from __future__ import annotations

from ..field_descriptions import (
    BOOK_DATE,
    EX_DATE,
    MOVEMENTS,
    PORTFOLIO_NUMBER,
    REFERENCE,
    STANDARDIZED_TRANSACTION_TYPE,
    SUBJECT_INSTRUMENT,
    TRADE_DATE,
    TRANSACTION_DESCRIPTION,
    TRANSACTION_TYPE,
    VALUE_DATE,
)
from .base import SchemaModel, date, schema_field
from .enums import StandardizedTransactionType as StandardizedTransactionTypeEnum
from .instrument import Instrument as InstrumentModel
from .movement import Movement as MovementModel


class JTransaction(SchemaModel):
    """A financial event consisting of one or more value movements."""

    PortfolioNumber: str = schema_field(
        description=PORTFOLIO_NUMBER,
    )
    TransactionType: str = schema_field(
        description=TRANSACTION_TYPE,
    )
    StandardizedTransactionType: StandardizedTransactionTypeEnum = schema_field(
        description=STANDARDIZED_TRANSACTION_TYPE,
    )
    TransactionDescription: str = schema_field(
        description=TRANSACTION_DESCRIPTION,
    )
    TradeDate: date = schema_field(
        description=TRADE_DATE,
    )
    BookDate: date = schema_field(
        description=BOOK_DATE,
    )
    ValueDate: date = schema_field(
        description=VALUE_DATE,
    )
    ExDate: date | None = schema_field(
        description=EX_DATE,
        default=None,
    )
    Reference: str | None = schema_field(
        description=REFERENCE,
        default=None,
    )
    Movements: list[MovementModel] = schema_field(
        description=MOVEMENTS,
        default_factory=list,
    )
    SubjectInstrument: InstrumentModel | None = schema_field(
        description=SUBJECT_INSTRUMENT,
        default=None,
    )
