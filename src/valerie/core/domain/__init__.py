"""Domain framework for pluggable business domains."""

from .base import BaseDomain, DomainIntent
from .registry import DomainRegistry

__all__ = ["BaseDomain", "DomainIntent", "DomainRegistry"]
