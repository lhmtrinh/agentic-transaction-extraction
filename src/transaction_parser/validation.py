from __future__ import annotations

import re

from .models import ValidationIssue
from .types import JSONDict


def validate_payload(payload: JSONDict | None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    payload = payload or {}
    transactions = payload.get("Transactions")

    if not isinstance(transactions, list):
        issues.append(ValidationIssue("error", "Top-level Transactions must be a list."))
        return issues
    if not transactions:
        issues.append(ValidationIssue("error", "Transactions must not be empty."))
        return issues

    for i, tx in enumerate(transactions):
        code = tx.get("StandardizedTransactionType")
        movements = tx.get("Movements") or []

        if not isinstance(movements, list):
            issues.append(ValidationIssue("error", f"Transaction {i}: Movements must be a list."))
            continue

        instrument_types = [
            movement.get("Instrument", {}).get("Type")
            for movement in movements
            if isinstance(movement, dict)
        ]

        if code == "Buy":
            if "Security" not in instrument_types:
                issues.append(ValidationIssue("error", f"Transaction {i}: Buy should contain a security movement."))
            if "Account" not in instrument_types:
                issues.append(ValidationIssue("error", f"Transaction {i}: Buy should contain a cash/account movement."))
        if code in {"Sell", "Redemption"}:
            if "Security" not in instrument_types:
                issues.append(ValidationIssue("error", f"Transaction {i}: {code} should contain a security movement."))
            if "Account" not in instrument_types:
                issues.append(ValidationIssue("error", f"Transaction {i}: {code} should contain a cash/account movement."))
        if code in {"Dividend", "Interest"} and tx.get("SubjectInstrument") is None:
            issues.append(ValidationIssue("warning", f"Transaction {i}: {code} should usually include SubjectInstrument."))
        if code in {"Buy", "Sell", "Redemption"} and tx.get("SubjectInstrument") is not None:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"Transaction {i}: SubjectInstrument should usually be null when a security movement exists.",
                )
            )

        portfolio_number = tx.get("PortfolioNumber")
        if portfolio_number in (None, ""):
            issues.append(
                ValidationIssue(
                    "error",
                    f"Transaction {i}: PortfolioNumber should be populated or use PORTNUM fallback.",
                )
            )

        for j, movement in enumerate(movements):
            instrument = movement.get("Instrument", {})
            if instrument.get("Type") == "Account":
                references = instrument.get("References")
                reference_keys = set()
                if isinstance(references, list):
                    for reference in references:
                        if not isinstance(reference, dict):
                            continue
                        key = reference.get("Key")
                        value = reference.get("Value")
                        if isinstance(key, str) and value not in (None, ""):
                            reference_keys.add(key)
                if movement.get("Price") != 1:
                    issues.append(
                        ValidationIssue(
                            "error",
                            f"Transaction {i}, movement {j}: Account movement should have Price = 1.",
                        )
                    )
                if not isinstance(movement.get("Amounts"), list):
                    issues.append(
                        ValidationIssue(
                            "error",
                            f"Transaction {i}, movement {j}: Account movement Amounts must be a list.",
                        )
                    )
                if "IBAN" not in reference_keys and "AccountNumber" not in reference_keys:
                    issues.append(
                        ValidationIssue(
                            "error",
                            f"Transaction {i}, movement {j}: Account movement should include IBAN or account number reference.",
                        )
                    )

        for field_name in ("TradeDate", "BookDate", "ValueDate", "ExDate"):
            value = tx.get(field_name)
            if value is None:
                continue
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                issues.append(
                    ValidationIssue("warning", f"Transaction {i}: {field_name} is not normalized to YYYY-MM-DD.")
                )

    return issues


def plan_targeted_repairs(issues: list[ValidationIssue]) -> list[str]:
    actions: list[str] = []
    messages = " ".join(issue.message for issue in issues)

    if any(token in messages for token in ("PortfolioNumber", "TradeDate", "BookDate", "ValueDate", "ExDate")):
        actions.append("overview_globals")
    if "Top-level Transactions must be a list" in messages or "Transactions must not be empty" in messages:
        actions.append("classification")
    if any(token in messages for token in ("security movement", "SubjectInstrument")):
        actions.append("security")
    if any(
        token in messages
        for token in ("cash/account movement", "Account movement", "Price = 1", "Amounts", "IBAN", "account number reference")
    ):
        actions.append("cash")

    return actions
