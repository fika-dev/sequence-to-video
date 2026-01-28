from domains.sequencing.strategies.appeal_first import AppealFirstStrategy
from domains.sequencing.strategies.base import SequencingStrategy
from domains.sequencing.strategies.default import DefaultStrategy
from domains.sequencing.strategies.footage_aware import FootageAwareStrategy
from domains.sequencing.strategies.reference_guided import ReferenceGuidedStrategy

STRATEGIES: dict[str, type[SequencingStrategy]] = {
    "default": DefaultStrategy,
    "footage_aware": FootageAwareStrategy,
    "appeal_first": AppealFirstStrategy,
    "reference_guided": ReferenceGuidedStrategy,
}


def load_strategy(name: str) -> SequencingStrategy:
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Unknown strategy: {name}. Available: {available}")
    return STRATEGIES[name]()


__all__ = [
    "SequencingStrategy",
    "DefaultStrategy",
    "FootageAwareStrategy",
    "AppealFirstStrategy",
    "ReferenceGuidedStrategy",
    "STRATEGIES",
    "load_strategy",
]
