"""Configuration settings for the chatbot."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# =============================================================================
# Model Registry - Centralized Model Configuration
# =============================================================================


class ModelRegistry:
    """Centralized registry for LLM model configurations.

    Loads from config/model-registry.yaml and provides methods to get
    model names based on provider, tier, or agent.
    """

    _instance: "ModelRegistry | None" = None
    _registry: dict[str, Any] = {}

    def __new__(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_registry()
        return cls._instance

    def _load_registry(self) -> None:
        """Load the model registry from YAML file."""
        # Find the config file relative to this module
        config_paths = [
            Path(__file__).parent.parent.parent.parent / "config" / "model-registry.yaml",
            Path.cwd() / "config" / "model-registry.yaml",
            Path("/app/config/model-registry.yaml"),  # Docker path
        ]

        for path in config_paths:
            if path.exists():
                with open(path) as f:
                    self._registry = yaml.safe_load(f)
                return

        # Fallback to defaults if file not found
        self._registry = self._get_defaults()

    def _get_defaults(self) -> dict[str, Any]:
        """Return default configuration if registry file not found."""
        return {
            "providers": {
                "anthropic": {
                    "models": {
                        "default": "claude-sonnet-4-20250514",
                        "fast": "claude-3-5-haiku-20241022",
                        "quality": "claude-opus-4-20250514",
                        "evaluation": "claude-3-5-sonnet-20241022",
                    }
                },
                "ollama": {
                    "models": {
                        "default": "llama3.2",
                        "fast": "llama3.2:3b",
                        "quality": "llama3.2:70b",
                        "evaluation": "llama3.2",
                    }
                },
                "groq": {
                    "models": {
                        "default": "llama-3.3-70b-versatile",
                        "fast": "llama-3.1-8b-instant",
                        "quality": "llama-3.3-70b-versatile",
                        "evaluation": "llama-3.3-70b-versatile",
                    }
                },
            },
            "defaults": {"provider": "ollama"},
            "agent_assignments": {},
            "parameters": {
                "default": {"temperature": 0.1, "max_tokens": 4096},
                "fast": {"temperature": 0.0, "max_tokens": 1024},
                "quality": {"temperature": 0.1, "max_tokens": 4096},
            },
        }

    @property
    def default_provider(self) -> str:
        """Get the default provider name.

        Respects VALERIE_USE_PAID_LLM toggle:
        - true: Use anthropic (paid)
        - false: Use ollama (free, default)
        """
        # Check for explicit provider override first
        env_provider = os.getenv("VALERIE_LLM_PROVIDER")

        # Check the paid LLM toggle
        use_paid = os.getenv("VALERIE_USE_PAID_LLM", "false").lower()
        if use_paid in ("true", "1", "yes"):
            return env_provider if env_provider else "anthropic"

        if env_provider:
            return env_provider

        return self._registry.get("defaults", {}).get("provider", "ollama")

    @property
    def is_using_paid_llm(self) -> bool:
        """Check if using paid LLM provider."""
        return self.default_provider == "anthropic"

    @property
    def is_using_free_llm(self) -> bool:
        """Check if using free LLM provider."""
        return self.default_provider in ("ollama", "groq")

    def get_model(self, provider: str | None = None, tier: str = "default") -> str:
        """Get model name for a provider and tier.

        Args:
            provider: Provider name (anthropic, ollama, groq). Defaults to default_provider.
            tier: Model tier (default, fast, quality, evaluation).

        Returns:
            Model name string.
        """
        provider = provider or self.default_provider
        providers = self._registry.get("providers", {})

        if provider not in providers:
            return "llama3.2"  # Ultimate fallback

        models = providers[provider].get("models", {})
        return models.get(tier, models.get("default", "llama3.2"))

    def get_model_for_agent(self, agent_name: str, provider: str | None = None) -> str:
        """Get the appropriate model for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., 'orchestrator', 'intent_classifier').
            provider: Provider to use. Defaults to default_provider.

        Returns:
            Model name string.
        """
        provider = provider or self.default_provider
        agent_assignments = self._registry.get("agent_assignments", {})

        # Find which tier this agent belongs to
        for tier_name, tier_config in agent_assignments.items():
            agents = tier_config.get("agents", [])
            if agent_name in agents:
                model_tier = tier_config.get("model_tier", "default")
                return self.get_model(provider, model_tier)

        # Default tier if agent not found
        return self.get_model(provider, "default")

    def get_parameters_for_agent(self, agent_name: str) -> dict[str, Any]:
        """Get model parameters for a specific agent.

        Args:
            agent_name: Name of the agent.

        Returns:
            Dictionary with temperature, max_tokens, etc.
        """
        # Check for agent-specific overrides first
        overrides = self._registry.get("agent_overrides", {})
        if agent_name in overrides:
            base_params = self.get_parameters_for_tier("default")
            base_params.update(overrides[agent_name])
            return base_params

        # Find the tier for this agent
        agent_assignments = self._registry.get("agent_assignments", {})
        for tier_name, tier_config in agent_assignments.items():
            if agent_name in tier_config.get("agents", []):
                model_tier = tier_config.get("model_tier", "default")
                return self.get_parameters_for_tier(model_tier)

        return self.get_parameters_for_tier("default")

    def get_parameters_for_tier(self, tier: str) -> dict[str, Any]:
        """Get default parameters for a model tier.

        Args:
            tier: Model tier (default, fast, quality, evaluation).

        Returns:
            Dictionary with temperature, max_tokens, timeout_seconds.
        """
        parameters = self._registry.get("parameters", {})
        defaults = {"temperature": 0.1, "max_tokens": 4096, "timeout_seconds": 60}

        if tier in parameters:
            defaults.update(parameters[tier])

        return defaults

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get full configuration for a provider.

        Args:
            provider: Provider name.

        Returns:
            Provider configuration dictionary.
        """
        return self._registry.get("providers", {}).get(provider, {})

    def get_fallback_chain(self) -> list[str]:
        """Get the fallback provider chain."""
        return self._registry.get("defaults", {}).get(
            "fallback_chain", ["ollama", "groq", "anthropic"]
        )

    def get_environment_config(self, environment: str) -> dict[str, Any]:
        """Get configuration for a specific environment.

        Args:
            environment: Environment name (development, staging, production).

        Returns:
            Environment configuration dictionary.
        """
        return self._registry.get("environments", {}).get(environment, {})

    def reload(self) -> None:
        """Reload the registry from file."""
        self._load_registry()


@lru_cache
def get_model_registry() -> ModelRegistry:
    """Get cached ModelRegistry instance."""
    return ModelRegistry()


# =============================================================================
# Application Settings
# =============================================================================


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(
        env_prefix="VALERIE_",
        env_file=".env",
        extra="ignore",
    )

    # LLM Configuration
    # Note: Default values come from config/model-registry.yaml
    # Use get_model_registry() for dynamic model selection per agent
    llm_provider: str = "ollama"  # Default provider (can override with env var)
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    model_name: str = ""  # Will use registry default if empty
    temperature: float = 0.1
    max_tokens: int = 4096

    def get_model_name(self) -> str:
        """Get the model name, using registry default if not set."""
        if self.model_name:
            return self.model_name
        registry = get_model_registry()
        return registry.get_model(self.llm_provider, "default")

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    session_ttl_seconds: int = 3600

    # Oracle Fusion Configuration
    oracle_base_url: str = "http://localhost:3000"
    oracle_client_id: str = "test"
    oracle_client_secret: str = "test"

    # Guardrails Configuration
    pii_detection_enabled: bool = True
    itar_detection_enabled: bool = True
    max_input_length: int = 5000

    # HITL Configuration
    hitl_enabled: bool = True
    hitl_timeout_ms: int = 86400000  # 24 hours
    high_risk_threshold: float = 0.7
    low_confidence_threshold: float = 0.6

    # Observability
    langsmith_api_key: str = ""
    langsmith_project: str = "valerie-chatbot"
    tracing_enabled: bool = True

    # Fallback Configuration
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    max_retries: int = 3

    # Evaluation
    evaluation_enabled: bool = True
    evaluation_sample_rate: float = 0.1


def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
