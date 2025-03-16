import httpx
from typing import Dict, Any, Optional
from loguru import logger

from .config import get_config


class SerperClient:
    """Client for Serper.dev Google Search API."""

    def __init__(self):
        config = get_config()
        self.api_key = config.get("serper", {}).get("api_key")
        self.base_url = config.get("serper", {}).get("base_url", "https://google.serper.dev/search")
        self.client = httpx.Client(timeout=30.0)

    def search(self, query: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform a search using Serper API.
        
        Args:
            query: Search query
            options: Additional options for the search
            
        Returns:
            Dict containing search results
        """
        if not self.api_key:
            raise ValueError("Serper API key not configured")

        if options is None:
            options = {}

        # Default options
        payload = {
            "q": query,
            "gl": options.get("gl", "cn"),  # Country for search results, cn 中国；us 美国
            "num": options.get("num", 10)  # Number of results
        }

        # Add any additional options
        for key, value in options.items():
            if key not in payload:
                payload[key] = value

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            logger.debug(f"Searching Serper with query: {query}")
            response = self.client.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            # Transform the result to match the expected format from Firecrawl
            transformed_result = self._transform_result(result, query)
            return transformed_result

        except Exception as e:
            logger.error(f"Error searching with Serper: {str(e)}")
            raise

    def _transform_result(self, serper_result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Transform Serper API result to match the expected format from Firecrawl.
        
        Args:
            serper_result: Raw result from Serper API
            query: Original search query
            
        Returns:
            Transformed result in Firecrawl-compatible format
        """
        transformed_data = []

        # Process organic results
        if "organic" in serper_result:
            for item in serper_result["organic"]:
                content = ""
                if "snippet" in item:
                    content += item["snippet"] + "\n\n"

                # Add any additional content from the result
                if "description" in item:
                    content += item["description"] + "\n\n"

                transformed_item = {
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "content": content.strip(),
                    "source": "serper"
                }
                transformed_data.append(transformed_item)

        # Process knowledge graph if available
        if "knowledgeGraph" in serper_result:
            kg = serper_result["knowledgeGraph"]
            content = ""
            if "description" in kg:
                content += kg["description"] + "\n\n"

            # Add attributes from knowledge graph
            if "attributes" in kg:
                for key, value in kg["attributes"].items():
                    content += f"{key}: {value}\n"

            transformed_item = {
                "url": kg.get("website", kg.get("link", "")),
                "title": kg.get("title", "Knowledge Graph Result"),
                "content": content.strip(),
                "source": "serper_knowledge_graph"
            }
            transformed_data.append(transformed_item)

        # Process answer box if available
        if "answerBox" in serper_result:
            ab = serper_result["answerBox"]
            content = ""
            if "answer" in ab:
                content += ab["answer"] + "\n\n"
            elif "snippet" in ab:
                content += ab["snippet"] + "\n\n"

            transformed_item = {
                "url": ab.get("link", ""),
                "title": ab.get("title", "Featured Snippet"),
                "content": content.strip(),
                "source": "serper_answer_box"
            }
            transformed_data.append(transformed_item)

        return {
            "query": query,
            "data": transformed_data
        }
