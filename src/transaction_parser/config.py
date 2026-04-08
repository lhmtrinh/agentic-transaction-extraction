from __future__ import annotations

from .models import StepSpec
from .types import JSONDict


DEFAULT_STEPS: dict[str, StepSpec] = {
    "overview_globals": StepSpec(
        "overview_globals",
        "00_overview_and_globals.txt",
        max_new_tokens=768,
        allow_reasoning_text=False,
    ),
    "classification": StepSpec(
        "classification",
        "01_classify_transaction.txt",
        max_new_tokens=384,
        allow_reasoning_text=False,
    ),
    "pattern": StepSpec(
        "pattern",
        "02_choose_pattern.txt",
        max_new_tokens=256,
        allow_reasoning_text=False,
    ),
    "security": StepSpec("security", "03_extract_security.txt", max_new_tokens=640, allow_reasoning_text=False),
    "cash": StepSpec("cash", "04_extract_cash_account.txt", max_new_tokens=768, allow_reasoning_text=False),
    "repair": StepSpec("repair", "05_repair_if_needed.txt", max_new_tokens=768, allow_reasoning_text=False),
}


PATTERN_TEMPLATES: dict[str, JSONDict] = {
    "Buy": {
        "StandardizedTransactionType": "Buy",
        "UseSubjectInstrument": False,
        "ExpectedMovements": [
            {"Role": "Security", "InstrumentType": "Security", "ExpectedDirection": "Positive"},
            {"Role": "Cash", "InstrumentType": "Account", "ExpectedDirection": "Negative"},
        ],
    },
    "Sell": {
        "StandardizedTransactionType": "Sell",
        "UseSubjectInstrument": False,
        "ExpectedMovements": [
            {"Role": "Security", "InstrumentType": "Security", "ExpectedDirection": "Negative"},
            {"Role": "Cash", "InstrumentType": "Account", "ExpectedDirection": "Positive"},
        ],
    },
    "Dividend": {
        "StandardizedTransactionType": "Dividend",
        "UseSubjectInstrument": True,
        "ExpectedMovements": [
            {"Role": "Cash", "InstrumentType": "Account", "ExpectedDirection": "Positive"},
        ],
    },
    "Interest": {
        "StandardizedTransactionType": "Interest",
        "UseSubjectInstrument": True,
        "ExpectedMovements": [
            {"Role": "Cash", "InstrumentType": "Account", "ExpectedDirection": "Positive"},
        ],
    },
    "Fee": {
        "StandardizedTransactionType": "Fee",
        "UseSubjectInstrument": False,
        "ExpectedMovements": [
            {"Role": "Cash", "InstrumentType": "Account", "ExpectedDirection": "Negative"},
        ],
    },
    "Redemption": {
        "StandardizedTransactionType": "Redemption",
        "UseSubjectInstrument": False,
        "ExpectedMovements": [
            {"Role": "Security", "InstrumentType": "Security", "ExpectedDirection": "Negative"},
            {"Role": "Cash", "InstrumentType": "Account", "ExpectedDirection": "Positive"},
        ],
    },
}
