from abc import ABC, abstractmethod
from typing import Any


class SequencingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def is_multi_step(self) -> bool:
        return False

    @abstractmethod
    def build_prompt(
        self,
        script: str,
        product_context: str | None = None,
        footage_catalog: str | None = None,
        lottie_presets_section: str = "",
        sfx_presets_section: str = "",
        scene_count: int = 10,
        step_context: dict[str, Any] | None = None,
    ) -> str:
        pass

    def get_steps(self) -> list[str]:
        return ["generate"]

    def parse_step_output(self, step: str, output: str) -> dict[str, Any]:
        return {}
