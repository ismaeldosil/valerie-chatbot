"""Core framework for multi-domain chatbot architecture."""

from .domain import BaseDomain, DomainIntent, DomainRegistry
from .state import CompositeState, CoreState

__all__ = [
    "BaseDomain",
    "DomainIntent",
    "DomainRegistry",
    "CoreState",
    "CompositeState",
]
