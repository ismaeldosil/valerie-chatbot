"""Business domains for the Valerie chatbot platform.

Each subdirectory represents a pluggable business domain that can be
registered with the DomainRegistry.

Available domains:
- supplier: Supplier management, compliance, and risk assessment
"""

from .supplier import SupplierDomain

__all__ = ["SupplierDomain"]
