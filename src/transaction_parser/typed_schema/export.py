from __future__ import annotations

from pathlib import Path
import json

from .base import SchemaModel, flatten_json_schema, render_model_json_schema, write_model_json_schema
from .instrument import Instrument
from .instrument_reference import InstrumentReference
from .movement import Movement
from .movement_amount import MovementAmount
from .transaction import JTransaction


SCHEMA_MODELS: tuple[type[SchemaModel], ...] = (
    JTransaction,
    Movement,
    Instrument,
    InstrumentReference,
    MovementAmount,
)


def build_contract_schema() -> dict[str, object]:
    return {
        model.__name__: flatten_json_schema(model.model_json_schema())
        for model in SCHEMA_MODELS
    }


def render_contract_schema(indent: int = 2) -> str:
    return json.dumps(build_contract_schema(), indent=indent, ensure_ascii=False)


def write_contract_schema(path: str | Path) -> None:
    Path(path).write_text(render_contract_schema() + "\n", encoding="utf-8")


__all__ = [
    "SCHEMA_MODELS",
    "build_contract_schema",
    "render_contract_schema",
    "write_contract_schema",
    "render_model_json_schema",
    "write_model_json_schema",
]
