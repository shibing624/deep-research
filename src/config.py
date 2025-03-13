import os
import yaml
from typing import Dict, Any, Optional
from loguru import logger

# Default configuration
DEFAULT_CONFIG = {
    "api": {
        "port": 3051
    },
    "openai": {
        "api_key": None,
        "base_url": "https://api.openai.com/v1",
        "model": "o3-mini"
    },
    "serper": {
        "api_key": None,
        "base_url": "https://google.serper.dev/search"
    },
    "research": {
        "default_breadth": 3,
        "default_depth": 2,
        "concurrency_limit": 2,
        "context_size": 128000
    }
}

# Global configuration object
_config = None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file with fallback to environment variables
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Dict containing configuration
    """
    global _config

    # Start with default configuration
    config = DEFAULT_CONFIG.copy()

    # Try to load from config file
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    # Merge with defaults (deep merge would be better but this is simple)
                    for section, values in yaml_config.items():
                        if section in config and isinstance(values, dict):
                            config[section].update(values)
                        else:
                            config[section] = values
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Error loading config from {config_path}: {str(e)}")
    else:
        # If no config file or it doesn't exist, look for a default config file
        default_paths = [
            './config.yaml',
            './config.example.yaml',
            './deep-research-config.yaml',
            os.path.expanduser('~/.deep-research/config.yaml')
        ]

        for path in default_paths:
            if os.path.exists(path):
                return load_config(path)

        logger.info("No configuration file found, using defaults and environment variables")

    # Override with environment variables
    # OpenAI
    if os.getenv("OPENAI_KEY"):
        config["openai"]["api_key"] = os.getenv("OPENAI_KEY")
    if os.getenv("OPENAI_ENDPOINT"):
        config["openai"]["base_url"] = os.getenv("OPENAI_ENDPOINT")
    if os.getenv("CUSTOM_MODEL"):
        config["openai"]["model"] = os.getenv("CUSTOM_MODEL")

    # Fireworks
    if os.getenv("FIREWORKS_KEY"):
        config["fireworks"]["api_key"] = os.getenv("FIREWORKS_KEY")

    # Firecrawl
    if os.getenv("FIRECRAWL_KEY"):
        config["firecrawl"]["api_key"] = os.getenv("FIRECRAWL_KEY")
    if os.getenv("FIRECRAWL_BASE_URL"):
        config["firecrawl"]["base_url"] = os.getenv("FIRECRAWL_BASE_URL")

    # Research settings
    if os.getenv("CONTEXT_SIZE"):
        try:
            config["research"]["context_size"] = int(os.getenv("CONTEXT_SIZE"))
        except (ValueError, TypeError):
            pass

    # Store the config globally
    _config = config
    return config


def get_config() -> Dict[str, Any]:
    """
    Get the current configuration
    
    Returns:
        Dict containing configuration
    """
    global _config
    if _config is None:
        return load_config()
    return _config
