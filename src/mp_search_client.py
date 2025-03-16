import httpx
from typing import Dict, Any, Optional
from loguru import logger

from .config import get_config


class MPSearchClient:
    """Client for MP Search API."""

    def __init__(self):
        config = get_config()
        self.api_key = config.get("mp_search", {}).get("api_key", "")
        self.base_url = config.get("mp_search", {}).get("base_url", "https://api.mpsrch.com/v1/search")
        self.forward_service = config.get("mp_search", {}).get("forward_service", "hyaide-application-1111")
        self.client = httpx.Client(timeout=30.0)

    def search(self, query: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform a search using MP Search API.
        
        Args:
            query: Search query
            options: Additional options for the search
            
        Returns:
            Dict containing search results
        """
        if not self.api_key:
            raise ValueError("MP Search API key not configured")

        if options is None:
            options = {}

        # Default payload
        payload = {
            "query": query,
            "forward_service": self.forward_service,
            "query_id": options.get("query_id", f"qid_{hash(query)}"),
            "stream": options.get("stream", False)
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            logger.debug(f"Searching with MP Search API: {query}")
            response = self.client.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            # Transform the result to match the expected format
            transformed_result = self._transform_result(result, query)
            logger.debug(f"Transformed result: {transformed_result}")
            return transformed_result

        except Exception as e:
            logger.error(f"Error searching with MP Search API: {str(e)}")
            raise

    def _transform_result(self, mp_result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Transform MP Search API result to match the expected format.
        
        Args:
            mp_result: Raw result from MP Search API
            query: Original search query
            
        Returns:
            Transformed result in compatible format
        """
        transformed_data = []

        try:
            # 直接使用result字段作为内容
            if "result" in mp_result and mp_result["result"]:
                result_str = mp_result["result"]

                transformed_item = {
                    "url": "",  # No URL in the response
                    "title": f"MP Search Result for: {query}",
                    "content": str(result_str)[:2000],
                    "source": "mp_search"
                }
                transformed_data.append(transformed_item)

        except Exception as e:
            logger.error(f"Error transforming MP Search result: {str(e)}")
            # Add a fallback item with the error
            transformed_item = {
                "url": "",
                "title": "MP Search Error",
                "content": f"Error processing result: {str(e)}\nRaw result: {mp_result}",
                "source": "mp_search_error"
            }
            transformed_data.append(transformed_item)

        return {
            "query": query,
            "data": transformed_data
        }
