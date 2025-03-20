# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description:
"""
import os
import yaml
from typing import Dict, Any, Optional
from loguru import logger

# Default configuration
DEFAULT_CONFIG = {
    "openai": {
        "api_key": None,
        "base_url": "https://api.openai.com/v1",
        "model": "o3-mini"
    },
    "serper": {
        "api_key": None,
        "base_url": "https://google.serper.dev/search"
    },
    "tavily": {
        "api_key": None,
        "base_url": "https://api.tavily.com/search"
    },
    "research": {
        "concurrency_limit": 1,
        "context_size": 128000,
        "search_source": "serper",
        "max_results_per_query": 5,
        "enable_refine_search_result": False,
        "enable_next_plan": False
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

    # Try to load from specified config file
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
        # If no config file specified, look for config.yaml in the current directory
        default_path = './config.yaml'
        if os.path.exists(default_path):
            return load_config(default_path)
        else:
            logger.info("No configuration file found, using defaults")

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
