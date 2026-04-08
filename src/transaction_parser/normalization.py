from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re

from .config import PATTERN_TEMPLATES
from .models import TransactionState
from .types import JSONDict


def log_decision(state: TransactionState, message: str) -> None:
    state.decision_log.append(message)
    if state.trace_callback is not None:
        state.trace_callback(f"[decision] {message}")


def normalize_date_value(value: object) -> object:
    if value is None or not isinstance(value, str):
        return value
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def normalize_overview_globals(payload: JSONDict | None) -> JSONDict:
    payload = deepcopy(payload or {})
    for field_name in ("TradeDate", "BookDate", "ValueDate", "ExDate"):
        payload[field_name] = normalize_date_value(payload.get(field_name))
    if payload.get("PortfolioNumber") in (None, ""):
        payload["PortfolioNumber"] = "PORTNUM"
    return payload


def normalize_payload_dates(payload: JSONDict | None) -> JSONDict:
    payload = deepcopy(payload or {})
    transactions = payload.get("Transactions")
    if not isinstance(transactions, list):
        return payload
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        for field_name in ("TradeDate", "BookDate", "ValueDate", "ExDate"):
            tx[field_name] = normalize_date_value(tx.get(field_name))
    return payload


def normalize_pattern(pattern: JSONDict | None, classification: JSONDict | None, state: TransactionState) -> JSONDict:
    pattern = deepcopy(pattern or {})
    classification = classification or {}
    standardized_code = pattern.get("StandardizedTransactionType") or classification.get("StandardizedTransactionType")
    template = PATTERN_TEMPLATES.get(standardized_code)
    if template is None:
        log_decision(state, "Pattern could not be normalized from a known transaction type.")
        return pattern

    normalized = deepcopy(template)
    if pattern.get("StandardizedTransactionType") != normalized["StandardizedTransactionType"]:
        log_decision(
            state,
            f"Normalized movement pattern from transaction type {normalized['StandardizedTransactionType']} using deterministic template.",
        )
    return normalized


def expected_roles(pattern: JSONDict | None) -> set[str]:
    movements = (pattern or {}).get("ExpectedMovements") or []
    return {
        movement.get("Role")
        for movement in movements
        if isinstance(movement, dict) and movement.get("Role")
    }


def should_run_security(pattern: JSONDict | None) -> bool:
    roles = expected_roles(pattern)
    return "Security" in roles or bool((pattern or {}).get("UseSubjectInstrument"))


def should_run_cash(pattern: JSONDict | None) -> bool:
    return "Cash" in expected_roles(pattern)


def should_retry_classification(classification: JSONDict | None) -> bool:
    classification = classification or {}
    confidence = classification.get("Confidence")
    transaction_type = classification.get("StandardizedTransactionType")
    return not transaction_type or confidence == "Low"
