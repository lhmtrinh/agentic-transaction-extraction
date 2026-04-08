from __future__ import annotations

from pathlib import Path
import json
from typing import TYPE_CHECKING, Callable

import torch
from PIL import Image

from .models import StepResult, StepSpec, TransactionState
from .types import JSONDict

if TYPE_CHECKING:
    from transformers import AutoModelForImageTextToText, AutoProcessor


class ModelRuntime:
    def __init__(
        self,
        model_id: str,
        device: str,
        dtype: torch.dtype,
        quantization: str | None = None,
        logger: Callable[[str], None] | None = None,
        show_prompt_text: bool = False,
        show_raw_model_output: bool = False,
    ) -> None:
        self.model_id = model_id
        self.device = device
        self.dtype = dtype
        self.quantization = quantization
        self.logger = logger
        self.show_prompt_text = show_prompt_text
        self.show_raw_model_output = show_raw_model_output
        self.processor = None
        self.model = None

    def _log(self, message: str) -> None:
        if self.logger is not None:
            self.logger(message)

    def load(self) -> None:
        if self.processor is not None and self.model is not None:
            self._log("[runtime] model already loaded; reusing existing model and processor.")
            return

        from transformers import AutoModelForImageTextToText, AutoProcessor

        self._log(
            f"[runtime] loading model={self.model_id} device={self.device} "
            f"dtype={self.dtype} quantization={self.quantization or 'none'}"
        )

        model_kwargs: JSONDict = {
            "device_map": self.device,
        }

        if self.quantization is None:
            model_kwargs["dtype"] = self.dtype
        else:
            try:
                from transformers import BitsAndBytesConfig
            except ImportError as exc:
                raise ImportError(
                    "Quantization was requested, but BitsAndBytesConfig is unavailable. "
                    "Install a transformers build with bitsandbytes support and the bitsandbytes package."
                ) from exc

            if self.quantization == "4bit":
                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=self.dtype,
                )
            elif self.quantization == "8bit":
                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_8bit=True,
                )
            else:
                raise ValueError("quantization must be one of: None, '4bit', '8bit'")

        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = AutoModelForImageTextToText.from_pretrained(
            self.model_id,
            **model_kwargs,
        )
        self._log("[runtime] model and processor loaded.")

    def load_image(self, image_path: str | Path) -> Image.Image:
        return Image.open(image_path).convert("RGB")

    def decode_first_json_object(self, text: str) -> JSONDict:
        decoder = json.JSONDecoder()
        last_error = None
        for idx, ch in enumerate(text):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[idx:])
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError as exc:
                last_error = exc
        raise ValueError(f"Could not parse JSON from model output. Last error: {last_error}")

    def decode_last_json_object(self, text: str) -> JSONDict:
        decoder = json.JSONDecoder()
        last_error = None
        last_object: JSONDict | None = None
        for idx, ch in enumerate(text):
            if ch != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[idx:])
                if isinstance(obj, dict):
                    last_object = obj
            except json.JSONDecodeError as exc:
                last_error = exc
        if last_object is not None:
            return last_object
        raise ValueError(f"Could not parse JSON from model output. Last error: {last_error}")

    def run_prompt(
        self,
        image: Image.Image,
        step: StepSpec,
        prompt_text: str,
        state: TransactionState,
        *,
        result_name: str | None = None,
    ) -> JSONDict:
        assert self.processor is not None
        assert self.model is not None
        stored_name = result_name or step.name
        self._log(f"[step:{stored_name}] starting.")
        if self.show_prompt_text:
            self._log(f"[step:{stored_name}] prompt:\n{prompt_text}")

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a financial extraction engine. "
                    "Return exactly one JSON object. "
                    "Do not explain. "
                    "Do not analyze. "
                    "Do not describe the image. "
                    "Do not output any text before or after the JSON. "
                    "Do not use markdown. "
                    "Do not use code fences. "
                    "Do not use comments."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt_text},
                ],
            },
        ]

        prompt = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.processor(text=[prompt], images=[image], return_tensors="pt")
        inputs = {
            key: value.to(self.model.device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }

        generation_kwargs: JSONDict = {
            "max_new_tokens": step.max_new_tokens,
            "do_sample": step.temperature > 0.0,
            "temperature": step.temperature,
            "top_p": 0.95,
            "top_k": 20,
            "repetition_penalty": 1.0,
            "pad_token_id": self.processor.tokenizer.eos_token_id,
        }

        if not generation_kwargs["do_sample"]:
            generation_kwargs.pop("temperature")
            generation_kwargs.pop("top_p")
            generation_kwargs.pop("top_k")

        with torch.no_grad():
            output_ids = self.model.generate(**inputs, **generation_kwargs)

        generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]
        raw_output = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        if self.show_raw_model_output:
            self._log(f"[step:{stored_name}] raw model output:\n{raw_output}")
        parsed_output = (
            self.decode_last_json_object(raw_output)
            if step.allow_reasoning_text
            else self.decode_first_json_object(raw_output)
        )
        state.step_results[stored_name] = StepResult(
            name=stored_name,
            prompt=prompt_text,
            raw_output=raw_output,
            parsed_output=parsed_output,
        )
        self._log(f"[step:{stored_name}] parsed JSON successfully.")
        return parsed_output
