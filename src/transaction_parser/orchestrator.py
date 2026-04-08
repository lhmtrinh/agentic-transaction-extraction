from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import torch
from PIL import Image

from .config import DEFAULT_STEPS
from .models import TransactionState, ValidationIssue
from .normalization import (
    log_decision,
    normalize_overview_globals,
    normalize_pattern,
    normalize_payload_dates,
    should_retry_classification,
    should_run_cash,
    should_run_security,
)
from .prompting import PromptRepository
from .runtime import ModelRuntime
from .schema_guidance import TransactionSchemaGuidance
from .step_models import render_step_output_schema
from .types import JSONDict
from .validation import plan_targeted_repairs, validate_payload


class TransactionOrchestrator:
    def __init__(
        self,
        root: str | Path = ".",
        model_id: str = "Qwen/Qwen3.5-0.8B",
        device: str = "cuda",
        dtype: torch.dtype = torch.float16,
        quantization: str | None = None,
        auto_repair: bool = True,
        max_targeted_repair_rounds: int = 2,
        verbose: bool = False,
        show_prompt_text: bool = False,
        show_raw_model_output: bool = False,
        runtime: ModelRuntime | None = None,
    ) -> None:
        self.root = Path(root)
        self.model_id = model_id
        self.device = device
        self.dtype = dtype
        self.quantization = quantization
        self.auto_repair = auto_repair
        self.max_targeted_repair_rounds = max_targeted_repair_rounds
        self.verbose = verbose
        self.show_prompt_text = show_prompt_text
        self.show_raw_model_output = show_raw_model_output
        self.prompts = PromptRepository(self.root / "prompts" / "pipeline")
        self.schema_guidance = TransactionSchemaGuidance()
        if runtime is None:
            self.runtime = ModelRuntime(
                model_id=model_id,
                device=device,
                dtype=dtype,
                quantization=quantization,
                logger=self._emit if verbose else None,
                show_prompt_text=show_prompt_text,
                show_raw_model_output=show_raw_model_output,
            )
        else:
            self.runtime = runtime
            self.runtime.logger = self._emit if verbose else None
            self.runtime.show_prompt_text = show_prompt_text
            self.runtime.show_raw_model_output = show_raw_model_output

    def _emit(self, message: str) -> None:
        if self.verbose:
            print(message)

    def _log_decision(self, state: TransactionState, message: str) -> None:
        log_decision(state, message)

    def run(self, image_path: str | Path) -> TransactionState:
        self._emit("[orchestrator] run started.")
        self.runtime.load()
        image_path = Path(image_path)
        state = TransactionState(image_path=image_path, trace_callback=self._emit if self.verbose else None)
        image = self.runtime.load_image(image_path)

        state.overview_globals = self._run_overview_globals(image, state)
        state.overview_globals = normalize_overview_globals(state.overview_globals)

        state.classification = self._run_classification(image, state)
        if should_retry_classification(state.classification):
            self._log_decision(state, "Classification confidence is low or missing type; retrying with a heading-focused hint.")
            state.retry_counts["classification"] = state.retry_counts.get("classification", 0) + 1
            state.classification = self._run_classification(
                image,
                state,
                extra_hint=(
                    "Focus on the strongest visible transaction heading or title. "
                    "Do not use reference numbers, IBANs, or account identifiers as TransactionType."
                ),
                result_name="classification_retry",
            )

        state.pattern = self._run_pattern(image, state)
        state.pattern = normalize_pattern(state.pattern, state.classification, state)

        if should_run_security(state.pattern):
            self._log_decision(state, "Pattern requires a security-side extraction.")
            state.security = self._run_security(image, state)
        else:
            self._log_decision(state, "Pattern does not require a security-side extraction; skipping security step.")
            state.security = {"SecurityMovement": None, "SubjectInstrument": None}

        if should_run_cash(state.pattern):
            self._log_decision(state, "Pattern requires a cash-side extraction.")
            state.cash = self._run_cash(image, state)
        else:
            self._log_decision(state, "Pattern does not require a cash-side extraction; skipping cash step.")
            state.cash = {"CashMovement": None}

        state.assembled = self._assemble_transaction(state)
        state.assembled = normalize_payload_dates(state.assembled)
        state.validations = validate_payload(state.assembled)

        final_payload = state.assembled
        if self.auto_repair and state.validations:
            self._log_decision(state, "Initial validation found issues; starting targeted repair loop.")
            final_payload = self._run_targeted_repair_loop(image, state) or final_payload

            targeted_issues = validate_payload(final_payload)
            if targeted_issues:
                self._log_decision(state, "Targeted repair still left issues; running broad final repair prompt.")
                state.repaired = self._run_broad_repair(image, state, final_payload, targeted_issues)
                state.repaired = normalize_payload_dates(state.repaired)
                state.final_validations = validate_payload(state.repaired)
            else:
                state.repaired = final_payload if final_payload != state.assembled else None
                state.final_validations = targeted_issues
        else:
            state.final_validations = list(state.validations)

        self._emit("[orchestrator] run finished.")
        return state

    def _json_text(self, value: object) -> str:
        return json.dumps(value, indent=2, ensure_ascii=False)

    def _run_overview_globals(
        self,
        image: Image.Image,
        state: TransactionState,
        *,
        extra_hint: str | None = None,
        result_name: str | None = None,
    ) -> JSONDict:
        step = DEFAULT_STEPS["overview_globals"]
        prompt = self.prompts.load(
            step.prompt_file,
            output_schema=render_step_output_schema("overview_globals"),
            relevant_field_guidance=self.schema_guidance.render_guidance("overview_globals"),
        )
        if extra_hint:
            prompt += "\n\nAdditional instruction:\n" + extra_hint
        return self.runtime.run_prompt(image, step, prompt, state, result_name=result_name)

    def _run_classification(
        self,
        image: Image.Image,
        state: TransactionState,
        *,
        extra_hint: str | None = None,
        result_name: str | None = None,
    ) -> JSONDict:
        step = DEFAULT_STEPS["classification"]
        prompt = self.prompts.load(
            step.prompt_file,
            output_schema=render_step_output_schema("classification"),
            relevant_field_guidance=self.schema_guidance.render_guidance("classification"),
        )
        prompt += "\n\nOverviewAndGlobals:\n" + self._json_text(state.overview_globals)
        if extra_hint:
            prompt += "\n\nAdditional instruction:\n" + extra_hint
        return self.runtime.run_prompt(image, step, prompt, state, result_name=result_name)

    def _run_pattern(self, image: Image.Image, state: TransactionState) -> JSONDict:
        step = DEFAULT_STEPS["pattern"]
        prompt = self.prompts.load(
            step.prompt_file,
            classification_json=self._json_text(state.classification),
            output_schema=render_step_output_schema("pattern"),
            relevant_field_guidance=self.schema_guidance.render_guidance("pattern"),
        )
        return self.runtime.run_prompt(image, step, prompt, state)

    def _run_security(
        self,
        image: Image.Image,
        state: TransactionState,
        *,
        extra_hint: str | None = None,
        result_name: str | None = None,
    ) -> JSONDict:
        step = DEFAULT_STEPS["security"]
        prompt = self.prompts.load(
            step.prompt_file,
            pattern_json=self._json_text(state.pattern),
            output_schema=render_step_output_schema("security"),
            relevant_field_guidance=self.schema_guidance.render_guidance("security"),
        )
        prompt += "\n\nOverviewAndGlobals:\n" + self._json_text(state.overview_globals)
        if extra_hint:
            prompt += "\n\nAdditional instruction:\n" + extra_hint
        return self.runtime.run_prompt(image, step, prompt, state, result_name=result_name)

    def _run_cash(
        self,
        image: Image.Image,
        state: TransactionState,
        *,
        extra_hint: str | None = None,
        result_name: str | None = None,
    ) -> JSONDict:
        step = DEFAULT_STEPS["cash"]
        prompt = self.prompts.load(
            step.prompt_file,
            pattern_json=self._json_text(state.pattern),
            output_schema=render_step_output_schema("cash"),
            relevant_field_guidance=self.schema_guidance.render_guidance("cash"),
        )
        prompt += "\n\nOverviewAndGlobals:\n" + self._json_text(state.overview_globals)
        prompt += "\n\nSecurity extraction:\n" + self._json_text(state.security)
        if extra_hint:
            prompt += "\n\nAdditional instruction:\n" + extra_hint
        return self.runtime.run_prompt(image, step, prompt, state, result_name=result_name)

    def _assemble_transaction(self, state: TransactionState) -> JSONDict:
        overview = deepcopy(state.overview_globals or {})
        classification = deepcopy(state.classification or {})
        pattern = deepcopy(state.pattern or {})
        security = deepcopy(state.security or {})
        cash = deepcopy(state.cash or {})

        security_movement = security.get("SecurityMovement")
        subject_instrument = security.get("SubjectInstrument")
        cash_movement = cash.get("CashMovement")

        movements: list[JSONDict] = []
        if isinstance(security_movement, dict):
            movements.append(security_movement)
        if isinstance(cash_movement, dict):
            movements.append(cash_movement)

        if isinstance(security_movement, dict) and subject_instrument is not None:
            self._log_decision(
                state,
                "Deterministic assembly cleared SubjectInstrument because a security movement is already present.",
            )
            subject_instrument = None

        transaction: JSONDict = {
            "PortfolioNumber": overview.get("PortfolioNumber") or "PORTNUM",
            "TransactionType": overview.get("TransactionType") or classification.get("TransactionType"),
            "StandardizedTransactionType": pattern.get("StandardizedTransactionType") or classification.get("StandardizedTransactionType"),
            "TransactionDescription": overview.get("TransactionDescription"),
            "TradeDate": overview.get("TradeDate"),
            "BookDate": overview.get("BookDate"),
            "ValueDate": overview.get("ValueDate"),
            "ExDate": overview.get("ExDate"),
            "Reference": overview.get("Reference"),
            "Movements": movements,
            "SubjectInstrument": subject_instrument,
        }

        return {"Transactions": [transaction]}

    def _run_broad_repair(
        self,
        image: Image.Image,
        state: TransactionState,
        draft_payload: JSONDict,
        issues: list[ValidationIssue],
    ) -> JSONDict:
        step = DEFAULT_STEPS["repair"]
        prompt = self.prompts.load(
            step.prompt_file,
            draft_json=self._json_text(draft_payload),
            issues_json=self._json_text(
                [{"severity": issue.severity, "message": issue.message} for issue in issues]
            ),
        )
        return self.runtime.run_prompt(image, step, prompt, state, result_name="broad_repair")

    def _run_targeted_repair_loop(self, image: Image.Image, state: TransactionState) -> JSONDict | None:
        current_payload = deepcopy(state.assembled or {})
        current_issues = list(state.validations)

        for round_index in range(1, self.max_targeted_repair_rounds + 1):
            actions = plan_targeted_repairs(current_issues)
            if not actions:
                self._log_decision(state, "No targeted repair actions were selected.")
                break

            self._log_decision(state, f"Targeted repair round {round_index}: {', '.join(actions)}.")

            if "overview_globals" in actions:
                state.retry_counts["overview_globals"] = state.retry_counts.get("overview_globals", 0) + 1
                state.overview_globals = self._run_overview_globals(
                    image,
                    state,
                    extra_hint="Re-check top-level identifiers and dates, especially PortfolioNumber, Reference, and date normalization.",
                    result_name=f"overview_globals_repair_{round_index}",
                )
                state.overview_globals = normalize_overview_globals(state.overview_globals)

            if "classification" in actions:
                state.retry_counts["classification"] = state.retry_counts.get("classification", 0) + 1
                state.classification = self._run_classification(
                    image,
                    state,
                    extra_hint="Re-check only the true transaction heading and type. Do not confuse it with reference or account numbers.",
                    result_name=f"classification_repair_{round_index}",
                )
                state.pattern = normalize_pattern(self._run_pattern(image, state), state.classification, state)

            if "security" in actions:
                state.retry_counts["security"] = state.retry_counts.get("security", 0) + 1
                state.security = self._run_security(
                    image,
                    state,
                    extra_hint=(
                        "Populate SubjectInstrument only when there is no security movement. "
                        "If SecurityMovement exists for a buy/sell/redemption, SubjectInstrument should be null."
                    ),
                    result_name=f"security_repair_{round_index}",
                )

            if "cash" in actions:
                state.retry_counts["cash"] = state.retry_counts.get("cash", 0) + 1
                state.cash = self._run_cash(
                    image,
                    state,
                    extra_hint=(
                        "Use the final cash result line for CashMovement.NetQuantity. "
                        "Do not use the security quantity as cash quantity. "
                        "Amounts must come from labeled cash rows only."
                    ),
                    result_name=f"cash_repair_{round_index}",
                )

            current_payload = self._assemble_transaction(state)
            current_payload = normalize_payload_dates(current_payload)
            current_issues = validate_payload(current_payload)
            if not current_issues:
                self._log_decision(state, f"Targeted repair round {round_index} resolved all validation issues.")
                return current_payload

        return current_payload
