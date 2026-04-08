from __future__ import annotations

from pathlib import Path
from typing import Any


class PromptRepository:
    def __init__(self, prompts_dir: str | Path) -> None:
        self.prompts_dir = Path(prompts_dir)

    def load(self, name: str, **kwargs: Any) -> str:
        template = (self.prompts_dir / name).read_text(encoding="utf-8")
        return template.format(**kwargs)
