"""Domain registry for managing pluggable business domains.

The DomainRegistry is a singleton that manages all registered domains,
handles domain discovery, and provides routing to the appropriate domain
based on user queries.
"""

import logging
from typing import Any

from .base import BaseDomain

logger = logging.getLogger(__name__)


class DomainRegistry:
    """Singleton registry for managing business domains.

    The registry provides:
    - Domain registration and discovery
    - Lookup by domain_id or keywords
    - Aggregated intent information across domains
    - Domain lifecycle management

    Example:
        # Register a domain
        registry = DomainRegistry()
        registry.register(SupplierDomain())

        # Get a domain by ID
        supplier = registry.get("supplier")

        # Find domain by keywords
        domain = registry.find_by_keywords(["vendor", "procurement"])
    """

    _instance: "DomainRegistry | None" = None
    _initialized: bool = False

    def __new__(cls) -> "DomainRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the registry."""
        if DomainRegistry._initialized:
            return

        self._domains: dict[str, BaseDomain] = {}
        self._keyword_index: dict[str, str] = {}  # keyword -> domain_id
        DomainRegistry._initialized = True
        logger.info("DomainRegistry initialized")

    def register(self, domain: BaseDomain) -> None:
        """Register a domain with the registry.

        Args:
            domain: The domain instance to register.

        Raises:
            ValueError: If a domain with the same ID is already registered.
        """
        if domain.domain_id in self._domains:
            raise ValueError(
                f"Domain '{domain.domain_id}' is already registered. "
                "Use unregister() first if you want to replace it."
            )

        self._domains[domain.domain_id] = domain

        # Index keywords for fast lookup
        for keyword in domain.get_keywords():
            keyword_lower = keyword.lower()
            if keyword_lower in self._keyword_index:
                existing = self._keyword_index[keyword_lower]
                logger.warning(
                    f"Keyword '{keyword}' already mapped to domain '{existing}', "
                    f"overwriting with '{domain.domain_id}'"
                )
            self._keyword_index[keyword_lower] = domain.domain_id

        logger.info(
            f"Registered domain '{domain.domain_id}' with {len(domain.get_keywords())} keywords"
        )

    def unregister(self, domain_id: str) -> BaseDomain | None:
        """Unregister a domain from the registry.

        Args:
            domain_id: The ID of the domain to unregister.

        Returns:
            The unregistered domain or None if not found.
        """
        domain = self._domains.pop(domain_id, None)
        if domain:
            # Remove keyword mappings
            keywords_to_remove = [k for k, v in self._keyword_index.items() if v == domain_id]
            for keyword in keywords_to_remove:
                del self._keyword_index[keyword]
            logger.info(f"Unregistered domain '{domain_id}'")
        return domain

    def get(self, domain_id: str) -> BaseDomain | None:
        """Get a domain by its ID.

        Args:
            domain_id: The domain identifier.

        Returns:
            The domain instance or None if not found.
        """
        return self._domains.get(domain_id)

    def get_all(self) -> dict[str, BaseDomain]:
        """Get all registered domains.

        Returns:
            Dictionary of domain_id to domain instance.
        """
        return self._domains.copy()

    def get_domain_ids(self) -> list[str]:
        """Get list of all registered domain IDs.

        Returns:
            List of domain IDs.
        """
        return list(self._domains.keys())

    def find_by_keyword(self, keyword: str) -> BaseDomain | None:
        """Find a domain by a single keyword.

        Args:
            keyword: The keyword to search for.

        Returns:
            The matching domain or None.
        """
        domain_id = self._keyword_index.get(keyword.lower())
        if domain_id:
            return self._domains.get(domain_id)
        return None

    def find_by_keywords(self, keywords: list[str]) -> BaseDomain | None:
        """Find the best matching domain for a list of keywords.

        Uses a scoring system to find the domain with the most keyword matches.

        Args:
            keywords: List of keywords to match.

        Returns:
            The best matching domain or None if no matches.
        """
        if not keywords:
            return None

        # Count matches per domain
        domain_scores: dict[str, int] = {}
        for keyword in keywords:
            domain_id = self._keyword_index.get(keyword.lower())
            if domain_id:
                domain_scores[domain_id] = domain_scores.get(domain_id, 0) + 1

        if not domain_scores:
            return None

        # Return domain with highest score
        best_domain_id = max(domain_scores.keys(), key=lambda d: domain_scores[d])
        return self._domains.get(best_domain_id)

    def get_all_intents(self) -> dict[str, list[str]]:
        """Get all intents across all domains.

        Returns:
            Dictionary of domain_id to list of intent values.
        """
        result: dict[str, list[str]] = {}
        for domain_id, domain in self._domains.items():
            intent_enum = domain.get_intent_enum()
            result[domain_id] = [e.value for e in intent_enum]
        return result

    def get_all_keywords(self) -> dict[str, list[str]]:
        """Get all keywords across all domains.

        Returns:
            Dictionary of domain_id to list of keywords.
        """
        result: dict[str, list[str]] = {}
        for domain_id, domain in self._domains.items():
            result[domain_id] = domain.get_keywords()
        return result

    def get_routing_table(self) -> dict[str, Any]:
        """Get the complete routing table for all domains.

        Used by the graph builder to configure routing.

        Returns:
            Dictionary with routing information for all domains.
        """
        return {
            "domains": {
                domain_id: domain.get_routing_info() for domain_id, domain in self._domains.items()
            },
            "keyword_index": self._keyword_index.copy(),
            "total_domains": len(self._domains),
        }

    def get_example_queries(self) -> dict[str, list[str]]:
        """Get example queries for all domains.

        Useful for help text and domain classification training.

        Returns:
            Dictionary of domain_id to list of example queries.
        """
        return {
            domain_id: domain.get_example_queries() for domain_id, domain in self._domains.items()
        }

    def clear(self) -> None:
        """Clear all registered domains.

        Primarily used for testing.
        """
        self._domains.clear()
        self._keyword_index.clear()
        logger.info("DomainRegistry cleared")

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance.

        Primarily used for testing to get a fresh registry.
        """
        cls._instance = None
        cls._initialized = False

    def __len__(self) -> int:
        """Return the number of registered domains."""
        return len(self._domains)

    def __contains__(self, domain_id: str) -> bool:
        """Check if a domain is registered."""
        return domain_id in self._domains

    def __repr__(self) -> str:
        """String representation of the registry."""
        domains = ", ".join(self._domains.keys()) if self._domains else "empty"
        return f"<DomainRegistry domains=[{domains}]>"
