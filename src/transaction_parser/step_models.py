from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .field_descriptions import (
    AMOUNT_CURRENCY,
    AMOUNT_DESCRIPTION,
    AMOUNT_QUANTITY,
    AMOUNT_STANDARDIZED_CODE,
    AMOUNTS,
    BOOK_DATE,
    EX_DATE,
    INSTRUMENT_NAME,
    INSTRUMENT_REFERENCES,
    MOVEMENTS,
    NET_QUANTITY,
    PORTFOLIO_NUMBER,
    PRICE,
    PRICE_CURRENCY,
    QUOTE_TYPE,
    REFERENCE,
    STANDARDIZED_TRANSACTION_TYPE,
    SUBJECT_INSTRUMENT,
    TRADE_DATE,
    TRANSACTION_DESCRIPTION,
    TRANSACTION_TYPE,
    VALUE_DATE,
)
from .typed_schema.base import flatten_json_schema
from .typed_schema.enums import (
    InstrumentType as InstrumentTypeEnum,
    MovementAmountStandardizedCode as MovementAmountStandardizedCodeEnum,
    QuoteType as QuoteTypeEnum,
    StandardizedTransactionType as StandardizedTransactionTypeEnum,
)


class StepModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
    )


class ConfidenceLevel(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class MovementRole(StrEnum):
    SECURITY = "Security"
    CASH = "Cash"


class Direction(StrEnum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"


class OverviewGlobalsResult(StepModel):
    PortfolioNumber: str = Field(description=PORTFOLIO_NUMBER)
    Reference: str | None = Field(default=None, description=REFERENCE)
    TransactionType: str | None = Field(default=None, description=TRANSACTION_TYPE)
    TransactionDescription: str | None = Field(default=None, description=TRANSACTION_DESCRIPTION)
    TradeDate: str | None = Field(default=None, description=TRADE_DATE)
    BookDate: str | None = Field(default=None, description=BOOK_DATE)
    ValueDate: str | None = Field(default=None, description=VALUE_DATE)
    ExDate: str | None = Field(default=None, description=EX_DATE)
    SecurityNameCandidate: str | None = Field(default=None, description=INSTRUMENT_NAME)
    DocumentSummary: str | None = Field(default=None, description="Very short transaction summary.")


class ClassificationResult(StepModel):
    StandardizedTransactionType: StandardizedTransactionTypeEnum | None = Field(
        default=None,
        description=STANDARDIZED_TRANSACTION_TYPE,
    )
    TransactionType: str | None = Field(default=None, description=TRANSACTION_TYPE)
    Confidence: ConfidenceLevel = Field(description="Classifier confidence.")


class ExpectedMovementPattern(StepModel):
    Role: MovementRole = Field(description="Logical role of the movement in the transaction.")
    InstrumentType: InstrumentTypeEnum = Field(description="Instrument type for the movement, usually Security or Account.")
    ExpectedDirection: Direction = Field(description="Expected sign direction from portfolio perspective.")


class PatternSelectionResult(StepModel):
    StandardizedTransactionType: StandardizedTransactionTypeEnum | None = Field(
        default=None,
        description=STANDARDIZED_TRANSACTION_TYPE,
    )
    UseSubjectInstrument: bool = Field(description="Whether the transaction should use SubjectInstrument instead of a moving security.")
    ExpectedMovements: list[ExpectedMovementPattern] = Field(
        default_factory=list,
        description=MOVEMENTS,
    )


class SecurityReferenceResult(StepModel):
    Key: Literal["ISIN", "Valor", "NKN"] = Field(description="Security reference key.")
    Value: str = Field(description="Security reference value exactly as shown in the document.")


class AccountReferenceResult(StepModel):
    Key: Literal["IBAN", "AccountNumber"] = Field(description="Account reference key.")
    Value: str = Field(description="Account reference value exactly as shown in the document.")


class SecurityInstrumentResult(StepModel):
    Type: Literal["Security"] = Field(description="Type of instrument.")
    Name: str | None = Field(default=None, description=INSTRUMENT_NAME)
    QuoteType: QuoteTypeEnum | None = Field(default=None, description=QUOTE_TYPE)
    References: list[SecurityReferenceResult] = Field(default_factory=list, description=INSTRUMENT_REFERENCES)


class SecurityMovementResult(StepModel):
    Instrument: SecurityInstrumentResult = Field(description="Instrument that actually moves in this flow.")
    NetQuantity: float | None = Field(default=None, description=NET_QUANTITY)
    Price: float | None = Field(default=None, description=PRICE)
    PriceCurrency: str | None = Field(default=None, description=PRICE_CURRENCY)
    Amounts: list[dict[str, object]] = Field(default_factory=list, description="Always empty for security extraction.")


class SubjectInstrumentResult(StepModel):
    Type: Literal["Security"] = Field(description="Type of instrument.")
    Name: str | None = Field(default=None, description=INSTRUMENT_NAME)
    QuoteType: QuoteTypeEnum | None = Field(default=None, description=QUOTE_TYPE)
    References: list[SecurityReferenceResult] = Field(default_factory=list, description=INSTRUMENT_REFERENCES)


class SecurityExtractionResult(StepModel):
    SecurityMovement: SecurityMovementResult | None = Field(default=None, description="Security movement, if the instrument actually moves.")
    SubjectInstrument: SubjectInstrumentResult | None = Field(default=None, description=SUBJECT_INSTRUMENT)


class CashInstrumentResult(StepModel):
    Type: Literal["Account"] = Field(description="Type of instrument.")
    Name: str = Field(description=INSTRUMENT_NAME)
    QuoteType: Literal["Piece"] = Field(description=QUOTE_TYPE)
    References: list[AccountReferenceResult] = Field(default_factory=list, description=INSTRUMENT_REFERENCES)


class CashAmountResult(StepModel):
    AmountDescription: str = Field(description=AMOUNT_DESCRIPTION)
    StandardizedCode: MovementAmountStandardizedCodeEnum = Field(description=AMOUNT_STANDARDIZED_CODE)
    Quantity: float = Field(description=AMOUNT_QUANTITY)
    Currency: str = Field(description=AMOUNT_CURRENCY)


class CashMovementResult(StepModel):
    Instrument: CashInstrumentResult = Field(description="Instrument that actually moves in this flow.")
    NetQuantity: float | None = Field(default=None, description=NET_QUANTITY)
    Price: Literal[1] = Field(description="Account price, expected to be 1.")
    PriceCurrency: str | None = Field(default=None, description=PRICE_CURRENCY)
    Amounts: list[CashAmountResult] = Field(default_factory=list, description=AMOUNTS)


class CashExtractionResult(StepModel):
    CashMovement: CashMovementResult | None = Field(default=None, description="Cash movement for the transaction.")


STEP_OUTPUT_MODELS: dict[str, type[StepModel]] = {
    "overview_globals": OverviewGlobalsResult,
    "classification": ClassificationResult,
    "pattern": PatternSelectionResult,
    "security": SecurityExtractionResult,
    "cash": CashExtractionResult,
}


def render_step_output_schema(step_name: str, indent: int = 2) -> str:
    model = STEP_OUTPUT_MODELS[step_name]
    schema = flatten_json_schema(model.model_json_schema())
    return render_output_skeleton(schema, indent=indent)


def _collapse_any_of(schema: dict) -> tuple[dict, bool]:
    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return schema, False

    non_null_entries: list[dict] = []
    nullable = False
    for entry in any_of:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "null":
            nullable = True
        else:
            non_null_entries.append(entry)

    if len(non_null_entries) == 1:
        return non_null_entries[0], nullable
    return schema, nullable


def _render_scalar_label(schema: dict, nullable: bool) -> str:
    if "const" in schema:
        label = str(schema["const"])
        if nullable:
            label += "|null"
        return f'"{label}"'

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        values = [str(value) for value in enum_values]
        if nullable and "null" not in values:
            values.append("null")
        return '"' + "|".join(values) + '"'

    schema_type = schema.get("type")
    label = str(schema_type) if isinstance(schema_type, str) else "value"
    if nullable:
        label += "|null"
    return f'"{label}"'


def _render_schema_lines(schema: dict, level: int, indent: int) -> list[str]:
    schema, nullable = _collapse_any_of(schema)
    pad = " " * (level * indent)
    schema_type = schema.get("type")

    if isinstance(schema.get("description"), str) and "Always empty" in schema["description"]:
        line = pad + "[]"
        if nullable:
            line += " | null"
        return [line]

    if schema_type == "object" and isinstance(schema.get("properties"), dict):
        lines = [pad + "{"]
        properties = list(schema["properties"].items())
        for index, (name, prop_schema) in enumerate(properties):
            child_lines = _render_schema_lines(prop_schema, level + 1, indent)
            child_indent = " " * ((level + 1) * indent)
            if len(child_lines) == 1:
                line = f'{child_indent}"{name}": {child_lines[0].lstrip()}'
                if index < len(properties) - 1:
                    line += ","
                lines.append(line)
                continue

            lines.append(f'{child_indent}"{name}": {child_lines[0].lstrip()}')
            for child_line in child_lines[1:-1]:
                lines.append(child_line)
            last_line = child_lines[-1]
            if index < len(properties) - 1:
                last_line += ","
            lines.append(last_line)

        closing = pad + "}"
        if nullable:
            closing += " | null"
        lines.append(closing)
        return lines

    if schema_type == "array" and isinstance(schema.get("items"), dict):
        item_lines = _render_schema_lines(schema["items"], level + 1, indent)
        lines = [pad + "["]
        if len(item_lines) == 1:
            lines.append((" " * ((level + 1) * indent)) + item_lines[0].lstrip() + ",")
        else:
            lines.extend(item_lines)
            lines[-1] += ","
        lines.append((" " * ((level + 1) * indent)) + "...")
        closing = pad + "]"
        if nullable:
            closing += " | null"
        lines.append(closing)
        return lines

    return [pad + _render_scalar_label(schema, nullable)]


def render_output_skeleton(schema: dict, indent: int = 2) -> str:
    return "\n".join(_render_schema_lines(schema, level=0, indent=indent))
