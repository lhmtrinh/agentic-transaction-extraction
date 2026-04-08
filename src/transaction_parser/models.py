from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .types import JSONDict


@dataclass(frozen=True)
class StepSpec:
    name: str
    prompt_file: str
    max_new_tokens: int
    temperature: float = 0.0
    allow_reasoning_text: bool = False


@dataclass
class StepResult:
    name: str
    prompt: str
    raw_output: str
    parsed_output: JSONDict


@dataclass
class ValidationIssue:
    severity: str
    message: str


@dataclass
class TransactionState:
    image_path: Path
    overview_globals: JSONDict | None = None
    classification: JSONDict | None = None
    pattern: JSONDict | None = None
    security: JSONDict | None = None
    cash: JSONDict | None = None
    assembled: JSONDict | None = None
    repaired: JSONDict | None = None
    validations: list[ValidationIssue] = field(default_factory=list)
    final_validations: list[ValidationIssue] = field(default_factory=list)
    decision_log: list[str] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)
    step_results: dict[str, StepResult] = field(default_factory=dict)
    trace_callback: Callable[[str], None] | None = None

    def final_payload(self) -> JSONDict | None:
        return self.repaired if self.repaired is not None else self.assembled

    def as_dict(self) -> JSONDict:
        return {
            "image_path": str(self.image_path),
            "overview_globals": self.overview_globals,
            "classification": self.classification,
            "pattern": self.pattern,
            "security": self.security,
            "cash": self.cash,
            "assembled": self.assembled,
            "repaired": self.repaired,
            "validations": [
                {"severity": issue.severity, "message": issue.message}
                for issue in self.validations
            ],
            "final_validations": [
                {"severity": issue.severity, "message": issue.message}
                for issue in self.final_validations
            ],
            "decision_log": list(self.decision_log),
            "retry_counts": dict(self.retry_counts),
        }
