"""Application configuration manager with environment-based settings."""

import os
from typing import Any

# Module-level config cache
_config_cache: dict[str, Any] = {}


def load_config(env: str = "development") -> dict[str, Any]:
    """Load configuration for the given environment.

    Args:
        env: Environment name ('development', 'staging', 'production').

    Returns:
        Configuration dictionary with database and API settings.
    """
    base_config = {
        "app_name": "MyApp",
        "debug": env == "development",
        "log_level": "DEBUG" if env == "development" else "INFO",
    }

    db_config = {
        "development": {
            "host": "localhost",
            "port": 5432,
            "name": "myapp_dev",
        },
        "staging": {
            "host": "staging-db.internal",
            "port": 5432,
            "name": "myapp_staging",
        },
        "production": {
            "host": "prod-db.internal",
            "port": 5432,
            "name": "myapp_prod",
        },
    }

    api_config = {
        "base_url": os.environ.get("API_BASE_URL", "http://localhost:8000"),
        "timeout": int(os.environ.get("API_TIMEOUT", "30")),
        "api_key": os.environ.get("API_KEY", "dev-key-placeholder"),
    }

    config = {
        **base_config,
        "database": db_config.get(env, db_config["development"]),
        "api": api_config,
    }

    # Cache the config
    _config_cache[env] = config
    return config


def get_cached_config(env: str = "development") -> dict[str, Any] | None:
    """Return cached config if available, otherwise None."""
    return _config_cache.get(env)


def clear_cache() -> None:
    """Clear the configuration cache."""
    _config_cache.clear()


def get_database_url(config: dict[str, Any]) -> str:
    """Build a database connection URL from config.

    Args:
        config: Configuration dictionary with 'database' key.

    Returns:
        PostgreSQL connection URL string.
    """
    db = config["database"]
    return f"postgresql://{db['host']}:{db['port']}/{db['name']}"
