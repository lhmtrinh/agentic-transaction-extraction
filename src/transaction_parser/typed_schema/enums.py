from __future__ import annotations

from enum import StrEnum


class StandardizedTransactionType(StrEnum):
    BUY = "Buy"
    SELL = "Sell"
    DIVIDEND = "Dividend"
    INTEREST = "Interest"
    REDEMPTION = "Redemption"
    FEE = "Fee"


class InstrumentType(StrEnum):
    SECURITY = "Security"
    ACCOUNT = "Account"


class QuoteType(StrEnum):
    PIECE = "Piece"
    PERCENTAGE = "Percentage"


class MovementAmountStandardizedCode(StrEnum):
    GROSS = "Gross"
    ACCRUED_INTEREST = "Accrued Interest"
    STAMP_DUTY = "Stamp Duty"
    EXCHANGE_FEE = "Exchange Fee"
    FOREIGN_COMMISSION = "Foreign Commission"
    BROKER_FEE = "Broker Fee"
    DELIVERY_FEE = "Delivery Fee"
    TRADING_FEE = "Trading Fee"
