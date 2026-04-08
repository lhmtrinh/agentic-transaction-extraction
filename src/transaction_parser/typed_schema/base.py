from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SchemaModel(BaseModel):
    """Base class for code-authored schema models."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=False,
    )


def schema_field(
    *,
    description: str,
    examples: list[Any] | None = None,
    default: Any = ...,
    default_factory: Any | None = None,
) -> Any:
    kwargs: dict[str, Any] = {"description": description}
    if examples is not None:
        kwargs["examples"] = examples
    if default_factory is not None:
        kwargs["default_factory"] = default_factory
        return Field(**kwargs)
    return Field(default=default, **kwargs)


def _resolve_refs(obj: Any, defs: dict[str, Any]) -> Any:
    if isinstance(obj, dict):
        if "$ref" in obj and isinstance(obj["$ref"], str):
            ref_name = obj["$ref"].split("/")[-1]
            return _resolve_refs(copy.deepcopy(defs[ref_name]), defs)
        return {key: _resolve_refs(value, defs) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_resolve_refs(item, defs) for item in obj]
    return obj


def flatten_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    working = copy.deepcopy(schema)
    defs = working.pop("$defs", {})
    return _resolve_refs(working, defs)


def render_model_json_schema(model: type[SchemaModel], indent: int = 2) -> str:
    schema = flatten_json_schema(model.model_json_schema())
    return json.dumps(schema, indent=indent, ensure_ascii=False)


def write_model_json_schema(model: type[SchemaModel], path: str | Path) -> None:
    Path(path).write_text(render_model_json_schema(model) + "\n", encoding="utf-8")


__all__ = [
    "SchemaModel",
    "schema_field",
    "flatten_json_schema",
    "render_model_json_schema",
    "write_model_json_schema",
    "date",
]
