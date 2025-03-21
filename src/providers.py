# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description:
"""
from typing import Dict, Any, Optional
import openai
from .config import get_config


def get_model(is_report: bool = False) -> Dict[str, Any]:
    """
    Get model configuration including client and model name.

    :param is_report: Whether to get the model configuration for a report
    
    Returns:
        Dict containing model configuration
    """
    config = get_config()
    if is_report:
        report_config = config.get("report_llm", {})
        api_key = report_config.get("api_key", "")
        model = report_config.get("model", "gpt-4o")
        base_url = report_config.get("base_url", None)
    else:
        openai_config = config.get("openai", {})
        api_key = openai_config.get("api_key", "")
        model = openai_config.get("model", "gpt-4o-mini")
        base_url = openai_config.get("base_url", None)

    # Initialize OpenAI client
    client_args = {"api_key": api_key}
    if base_url:
        client_args["base_url"] = base_url

    client = openai.OpenAI(**client_args)
    async_client = openai.AsyncOpenAI(**client_args)

    return {
        "client": client,
        "async_client": async_client,
        "model": model
    }


def get_search_provider(search_source=None):
    """
    Get the appropriate search provider based on configuration.

    Returns:
        An instance of the search provider class
    """
    if search_source is None:
        config = get_config()
        search_source = config.get("research", {}).get("search_source", "serper")

    if search_source == "mp_search":
        from .mp_search_client import MPSearchClient
        return MPSearchClient()
    elif search_source == "tavily":
        from .tavily_client import TavilyClient
        return TavilyClient()
    elif search_source == "qdrant":
        from .qdrant_client import QdrantSearchClient
        return QdrantSearchClient()
    else:  # Default to serper
        from .serper_client import SerperClient
        return SerperClient()
