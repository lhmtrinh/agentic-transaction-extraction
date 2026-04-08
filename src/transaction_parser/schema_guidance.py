from __future__ import annotations

from dataclasses import dataclass
import json

from .types import JSONDict
from .typed_schema.export import build_contract_schema


@dataclass(frozen=True)
class FieldSelection:
    entity: str
    field: str
    extra_rules: tuple[str, ...] = ()


STEP_FIELD_SELECTIONS: dict[str, tuple[FieldSelection, ...]] = {
    "overview_globals": (
        FieldSelection(
            "JTransaction",
            "PortfolioNumber",
            (
                "Extract portfolio, depot, or account identifier when visible.",
                "If missing after extraction, the deterministic pipeline will fall back to PORTNUM.",
                "Do not confuse portfolio/account identifiers with order references.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "Reference",
            (
                "Use bank reference, order number, or explicit reference identifier only.",
                "If no explicit reference exists, leave null.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "TransactionType",
            (
                "Use the exact transaction heading or label from the document.",
                "Do not replace TransactionType with a numeric reference or account number.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "TransactionDescription",
            (
                "Use a short raw description focused on the transaction or instrument.",
                "Prefer concise text rather than copying a large sentence block.",
                "If not sure, leave null.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "TradeDate",
            (
                "Normalize to YYYY-MM-DD.",
                "Use the execution or order date.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "BookDate",
            (
                "Normalize to YYYY-MM-DD.",
                "Use the booking or accounting date.",
                "If no separate booking date exists but one clear transaction date governs the booking, reuse that date.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "ValueDate",
            (
                "Normalize to YYYY-MM-DD.",
                "Use only an explicit settlement, value, or Valuta date.",
                "Do not confuse ValueDate with the document date or booking date.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "ExDate",
            (
                "Normalize to YYYY-MM-DD.",
                "Populate only when explicitly shown.",
                "Otherwise leave null.",
            ),
        ),
        FieldSelection(
            "Instrument",
            "Name",
            (
                "For this step, use it only as a broad SecurityNameCandidate if a main visible security name appears.",
            ),
        ),
    ),
    "classification": (
        FieldSelection(
            "JTransaction",
            "StandardizedTransactionType",
            (
                "Use this schema enum as the target transaction type set.",
                "Map the visible document heading to one of the allowed values only.",
                "If the document does not support a reliable classification, return null with lower confidence.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "TransactionType",
            (
                "Use the exact visible transaction heading or label from the document.",
                "Do not confuse TransactionType with a reference number, IBAN, or portfolio number.",
                "If not sure, leave null.",
            ),
        ),
    ),
    "pattern": (
        FieldSelection(
            "JTransaction",
            "StandardizedTransactionType",
            (
                "Use the classified standardized transaction type as the movement-template anchor.",
                "The pattern must stay consistent with the allowed transaction type enum.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "Movements",
            (
                "Movements are the actual value flows implied by the transaction type.",
                "Use the transaction type to decide whether Security and Cash flows are expected.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "SubjectInstrument",
            (
                "Use SubjectInstrument only when the instrument is context for the transaction and does not itself move.",
                "Typical cases are dividend and interest transactions.",
            ),
        ),
    ),
    "security": (
        FieldSelection(
            "Movement",
            "Instrument",
            (
                "In this step, Instrument belongs to the security side only.",
                "If a security actually moves, it belongs in SecurityMovement.Instrument.",
            ),
        ),
        FieldSelection(
            "Instrument",
            "Type",
            (
                'Use "Security" for security-side extraction in this step.',
            ),
        ),
        FieldSelection(
            "Instrument",
            "Name",
            (
                "Use the visible human-readable security name.",
            ),
        ),
        FieldSelection(
            "Instrument",
            "QuoteType",
            (
                'Use "Piece" for equities, ETFs, and funds.',
                'Use "Percentage" for bonds or nominal-based instruments.',
            ),
        ),
        FieldSelection(
            "Instrument",
            "References",
            (
                "Include only visible identifiers with Key equal to ISIN, Valor, or NKN.",
                "Do not invent missing identifiers.",
            ),
        ),
        FieldSelection(
            "Movement",
            "NetQuantity",
            (
                "Use the signed security quantity from portfolio perspective.",
                "Buy implies positive quantity; sell and redemption imply negative quantity.",
                "Do not calculate missing quantity.",
            ),
        ),
        FieldSelection(
            "Movement",
            "Price",
            (
                "Populate only when explicitly shown.",
                "Never calculate price from totals and quantity.",
            ),
        ),
        FieldSelection(
            "Movement",
            "PriceCurrency",
            (
                "Populate only if price is explicitly shown.",
            ),
        ),
        FieldSelection(
            "JTransaction",
            "SubjectInstrument",
            (
                "Use SubjectInstrument only when the instrument does not itself move.",
                "If SecurityMovement exists, SubjectInstrument should be null for the same instrument.",
                "Typical use cases are dividends and coupon/interest events.",
            ),
        ),
    ),
    "cash": (
        FieldSelection(
            "Movement",
            "Instrument",
            (
                "In this step, Instrument belongs to the cash account movement only.",
            ),
        ),
        FieldSelection(
            "Instrument",
            "Type",
            (
                'Use "Account" for the cash movement instrument.',
            ),
        ),
        FieldSelection(
            "Instrument",
            "Name",
            (
                "Use the visible cash account name if present.",
            ),
        ),
        FieldSelection(
            "Instrument",
            "QuoteType",
            (
                'Account movements should use "Piece".',
            ),
        ),
        FieldSelection(
            "Instrument",
            "References",
            (
                'Use Key="IBAN" when an IBAN is visible.',
                'Use Key="AccountNumber" when an account number is visible.',
                "If no IBAN or account number is visible, return an empty list.",
            ),
        ),
        FieldSelection(
            "Movement",
            "NetQuantity",
            (
                "Use the final cash result line only, such as total payable/receivable, debit, credit, Belastung, or Gutschrift.",
                "Do not reuse the security quantity as cash NetQuantity.",
                "If no final cash result line is visible, use null.",
            ),
        ),
        FieldSelection(
            "Movement",
            "Price",
            (
                "For account movements, Price must be 1.",
            ),
        ),
        FieldSelection(
            "Movement",
            "PriceCurrency",
            (
                "Use the cash account currency when visible.",
            ),
        ),
        FieldSelection(
            "Movement",
            "Amounts",
            (
                "Amounts apply to cash movement breakdown lines only.",
                "Extract only explicit labeled rows such as gross amount, fees, taxes, or accrued interest.",
                "If no labeled breakdown rows are visible, return an empty list.",
            ),
        ),
        FieldSelection(
            "MovementAmount",
            "AmountDescription",
            (
                "AmountDescription must be the exact textual label from the document.",
                "Do not use a number or currency token as AmountDescription.",
            ),
        ),
        FieldSelection(
            "MovementAmount",
            "StandardizedCode",
            (
                "Map the visible amount label to a normalized cash breakdown type such as Gross, Accrued Interest, Stamp Duty, Exchange Fee, Broker Fee, or Trading Fee.",
            ),
        ),
        FieldSelection(
            "MovementAmount",
            "Quantity",
            (
                "Use signed monetary values from portfolio perspective.",
                "Debit or charge lines are negative; credit lines are positive.",
            ),
        ),
        FieldSelection(
            "MovementAmount",
            "Currency",
            (
                "Use the visible amount currency.",
            ),
        ),
    ),
}


class TransactionSchemaGuidance:
    def __init__(self) -> None:
        self.schema_source = "typed_schema"
        self.schema = build_contract_schema()

    def _entity_schema(self, entity: str) -> JSONDict:
        entity_schema = self.schema.get(entity)
        if not isinstance(entity_schema, dict):
            raise KeyError(f"Unknown schema entity: {entity}")
        return entity_schema

    def _field_schema(self, entity: str, field: str) -> JSONDict:
        entity_schema = self._entity_schema(entity)
        properties = entity_schema.get("properties")
        if isinstance(properties, dict):
            field_schema = properties.get(field)
            if not isinstance(field_schema, dict):
                raise KeyError(f"Unknown field {entity}.{field}")
            return field_schema

        fields = entity_schema.get("fields")
        if isinstance(fields, dict):
            field_schema = fields.get(field)
            if field_schema is None:
                raise KeyError(f"Unknown field {entity}.{field}")
            if isinstance(field_schema, str):
                return {"type": field_schema}
            if isinstance(field_schema, dict):
                return field_schema

        raise KeyError(f"Entity {entity} does not define properties or fields.")

    def _field_types(self, field_schema: JSONDict) -> tuple[str | None, list[object] | None]:
        if "type" in field_schema:
            return field_schema.get("type"), field_schema.get("enum")
        any_of = field_schema.get("anyOf")
        if isinstance(any_of, list):
            types: list[str] = []
            enum_values: list[object] = []
            saw_enum = False
            for entry in any_of:
                if not isinstance(entry, dict):
                    continue
                entry_type = entry.get("type")
                if isinstance(entry_type, str):
                    types.append(entry_type)
                entry_enum = entry.get("enum")
                if isinstance(entry_enum, list):
                    enum_values.extend(entry_enum)
                    saw_enum = True
            type_label = "|".join(types) if types else None
            return type_label, enum_values if saw_enum else None
        return None, None

    def _field_header(self, entity: str, field: str, field_schema: JSONDict) -> str:
        field_type, enum_values = self._field_types(field_schema)
        parts = [f"- {entity}.{field}"]
        if isinstance(field_type, str):
            parts.append(f"(type: {field_type})")
        if isinstance(enum_values, list) and enum_values:
            allowed = ", ".join("null" if value is None else str(value) for value in enum_values)
            parts.append(f"(allowed: {allowed})")
        return " ".join(parts)

    def _field_description_lines(self, entity: str, field: str, selection: FieldSelection) -> list[str]:
        field_schema = self._field_schema(entity, field)
        lines = [self._field_header(entity, field, field_schema)]
        description = field_schema.get("description")
        if isinstance(description, str) and description.strip():
            lines.append(f"  - Schema meaning: {description.strip()}")
        _, enum_values = self._field_types(field_schema)
        if isinstance(enum_values, list) and enum_values:
            allowed = ", ".join("null" if value is None else str(value) for value in enum_values)
            lines.append(f"  - Enum rule: Choose only from these allowed values: {allowed}. Do not invent other values.")
        field_type, _ = self._field_types(field_schema)
        if isinstance(field_type, str) and "null" in field_type:
            lines.append("  - Null rule: If not sure, leave null.")

        items = field_schema.get("items")
        if isinstance(items, dict):
            title = items.get("title")
            if isinstance(title, str):
                lines.append(f"  - Nested item type: {title}")
            lines.append("  - Array rule: If multiple relevant visible items exist, include all of them in the array. Do not stop after one example item.")
        elif isinstance(items, str):
            lines.append(f"  - Nested item type: {items}")
            lines.append("  - Array rule: If multiple relevant visible items exist, include all of them in the array. Do not stop after one example item.")

        examples = field_schema.get("examples")
        if isinstance(examples, list) and examples:
            joined_examples = ", ".join("null" if value is None else str(value) for value in examples)
            lines.append(f"  - Examples: {joined_examples}")
        for rule in selection.extra_rules:
            lines.append(f"  - Rule: {rule}")
        return lines

    def render_guidance(self, step_name: str) -> str:
        selections = STEP_FIELD_SELECTIONS.get(step_name, ())
        if not selections:
            return ""
        lines = [f"Relevant field guidance (source: {self.schema_source}):"]
        for selection in selections:
            lines.extend(self._field_description_lines(selection.entity, selection.field, selection))
        return "\n".join(lines)
