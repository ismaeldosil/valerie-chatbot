"""Factory for creating data source instances based on configuration."""
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from valerie.data.interfaces import ISupplierDataSource


# ============================================================================
# Configuration Models
# ============================================================================

class SQLiteConfig(BaseModel):
    """SQLite data source configuration."""
    type: str = "sqlite"
    path: str = "data/valerie.db"


class APIConfig(BaseModel):
    """API data source configuration."""
    type: str = "api"
    base_url: str
    api_key: str | None = None
    timeout: int = 30
    retry_attempts: int = 3


class OracleConfig(BaseModel):
    """Oracle Fusion data source configuration."""
    type: str = "oracle"
    base_url: str
    client_id: str
    client_secret: str
    timeout: int = 30


class MockConfig(BaseModel):
    """Mock data source configuration."""
    type: str = "mock"


class DataSourceConfig(BaseModel):
    """Unified data source configuration."""
    type: str = "sqlite"
    # SQLite
    sqlite_path: str | None = None
    # API
    api_base_url: str | None = None
    api_key: str | None = None
    timeout: int = 30
    retry_attempts: int = 3
    # Oracle
    oracle_base_url: str | None = None
    oracle_client_id: str | None = None
    oracle_client_secret: str | None = None


class EnvironmentConfig(BaseModel):
    """Environment-specific configuration."""
    environments: dict[str, DataSourceConfig] = Field(default_factory=dict)
    default: str = "development"


# ============================================================================
# Factory Functions
# ============================================================================

def _expand_env_vars(value: Any) -> Any:
    """Recursively expand environment variables in config values."""
    if isinstance(value, str):
        # Handle ${VAR} syntax
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, value)
        return value
    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_expand_env_vars(v) for v in value]
    return value


def load_config(config_path: str | Path | None = None) -> DataSourceConfig:
    """
    Load data source configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses default location.

    Returns:
        DataSourceConfig for the current environment
    """
    if config_path is None:
        # Try common locations
        possible_paths = [
            Path("config/data-sources.yaml"),
            Path("valerie-chatbot/config/data-sources.yaml"),
            Path(__file__).parent.parent.parent.parent / "config" / "data-sources.yaml",
        ]
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

    if config_path is None or not Path(config_path).exists():
        # Return default SQLite config
        return DataSourceConfig(
            type="sqlite",
            sqlite_path="data/valerie.db"
        )

    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    # Expand environment variables
    raw_config = _expand_env_vars(raw_config)

    # Get current environment
    env = os.environ.get("VALERIE_ENV", raw_config.get("default", "development"))

    # Get environment-specific config
    environments = raw_config.get("environments", {})
    env_config = environments.get(env, {})

    return DataSourceConfig(**env_config)


def get_data_source(config: DataSourceConfig | None = None) -> ISupplierDataSource:
    """
    Factory function to create the appropriate data source.

    Args:
        config: Data source configuration. If None, loads from config file.

    Returns:
        ISupplierDataSource implementation

    Raises:
        ValueError: If the data source type is unknown
    """
    if config is None:
        config = load_config()

    if config.type == "sqlite":
        from valerie.data.sources.sqlite import SQLiteDataSource
        db_path = config.sqlite_path or "data/valerie.db"
        return SQLiteDataSource(db_path)

    elif config.type == "api":
        from valerie.data.sources.api import APIDataSource
        if not config.api_base_url:
            raise ValueError("API data source requires api_base_url")
        return APIDataSource(
            base_url=config.api_base_url,
            api_key=config.api_key,
            timeout=config.timeout
        )

    elif config.type == "oracle":
        from valerie.data.sources.oracle import OracleFusionDataSource
        if not all([config.oracle_base_url, config.oracle_client_id, config.oracle_client_secret]):
            raise ValueError("Oracle data source requires base_url, client_id, and client_secret")
        return OracleFusionDataSource(
            base_url=config.oracle_base_url,
            client_id=config.oracle_client_id,
            client_secret=config.oracle_client_secret,
            timeout=config.timeout
        )

    elif config.type == "mock":
        from valerie.data.sources.mock import MockDataSource
        return MockDataSource()

    else:
        raise ValueError(f"Unknown data source type: {config.type}")


# ============================================================================
# Singleton Instance
# ============================================================================

_data_source_instance: ISupplierDataSource | None = None


def get_default_data_source() -> ISupplierDataSource:
    """
    Get or create the default data source singleton.

    Returns:
        The default ISupplierDataSource instance
    """
    global _data_source_instance
    if _data_source_instance is None:
        _data_source_instance = get_data_source()
    return _data_source_instance


def reset_data_source():
    """Reset the default data source singleton (useful for testing)."""
    global _data_source_instance
    _data_source_instance = None


def set_data_source(data_source: ISupplierDataSource):
    """
    Set a custom data source (useful for testing/dependency injection).

    Args:
        data_source: The data source to use
    """
    global _data_source_instance
    _data_source_instance = data_source
