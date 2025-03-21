import sys

import httpx
from loguru import logger

sys.path.append("/")
from .config import get_config

import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import numpy as np


class EmbeddingGenerator(ABC):
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        pass

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.generate_embeddings([text])[0]

    @staticmethod
    def cosine_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vector1, vector2)
        magnitude = np.linalg.norm(vector1) * np.linalg.norm(vector2)
        return 0 if not magnitude else dot_product / magnitude


class QdrantEngine:
    def __init__(
            self,
            collection_name: str,
            embedding_generator: EmbeddingGenerator,
            qdrant_client_params: Dict[str, Any] = {"host": "localhost", "port": 6333},
            vector_size: int = 384,
            distance: Distance = Distance.COSINE,
    ):
        """
        Initialize the Qdrant vector store.

        :param collection_name: Name of the Qdrant collection.
        :param embedding_generator: An instance of EmbeddingGenerator to generate embeddings.
        :param qdrant_client_params: Dictionary of parameters to pass to QdrantClient.
        :param vector_size: Size of the vectors.
        :param distance: Distance metric for vector comparison (default is cosine similarity).
        """
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.embedding_generator = embedding_generator

        # Initialize QdrantClient with provided parameters
        self.client = QdrantClient(**qdrant_client_params)

        # Create collection if it doesn't exist
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=self.distance),
                timeout=500,
            )

    def upload_vectors(
            self, vectors: Union[np.ndarray, List[List[float]]],
            payload: List[Dict[str, Any]],
            batch_size: int = 256
    ):
        """
        Upload vectors and payload to the Qdrant collection.

        :param vectors: A numpy array or list of vectors to upload.
        :param payload: A list of dictionaries containing the payload for each vector.
        :param batch_size: Number of vectors to upload in a single batch.
        """
        if not isinstance(vectors, np.ndarray):
            vectors = np.array(vectors)
        if len(vectors) != len(payload):
            raise ValueError("Vectors and payload must have the same length.")
        self.client.upload_collection(
            collection_name=self.collection_name,
            vectors=vectors,
            payload=payload,
            ids=None,
            batch_size=batch_size,
        )

    def search(
            self, text: str,
            query_filter: Optional[Filter] = None,
            limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for the closest vectors in the collection based on the input text.

        :param text: The text query to search for.
        :param query_filter: Optional filter to apply to the search.
        :param limit: Number of closest results to return.
        :return: List of payloads from the closest vectors.
        """
        # Generate embedding using the provided embedding generator
        vector = self.embedding_generator.generate_embedding(text)

        # Search for closest vectors in the collection
        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
        ).points

        # Extract payloads from search results
        search_result = [{"payload": hit.payload, "score": hit.score} for hit in search_result]
        return search_result

    def build_filter(self, conditions: List[Dict[str, Any]]) -> Filter:
        """
        Build a Qdrant filter from a list of conditions.

        :param conditions: A list of conditions, where each condition is a dictionary with:
                          - key: The field name to filter on.
                          - match: The value to match (can be a string, number, or other supported types).
        :return: A Qdrant Filter object.
        """
        filter_conditions = []
        for condition in conditions:
            key = condition.get("key")
            match_value = condition.get("match")
            if key and match_value is not None:
                filter_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=match_value),
                    )
                )

        return Filter(must=filter_conditions)


class EmbeddingGenerator(ABC):
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        pass

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.generate_embeddings([text])[0]

    @staticmethod
    def cosine_similarity(vector1: np.ndarray, vector2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vector1, vector2)
        magnitude = np.linalg.norm(vector1) * np.linalg.norm(vector2)
        return 0 if not magnitude else dot_product / magnitude


class SentenceTransformerEmbedding(EmbeddingGenerator):
    def __init__(
            self,
            model_name_or_path: str = "sentence-transformers/multi-qa-mpnet-base-cos-v1",
            device: str = None
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SentenceTransformer(model_name_or_path, device=self.device)
        self.embedding_size = self.model.get_sentence_embedding_dimension()

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, show_progress_bar=False)


class QdrantSearchClient:
    """Client for Qdrant vector database search."""

    def __init__(self):
        config = get_config()
        qdrant_config = config.get("qdrant", {})

        self.collection_name = qdrant_config.get("qdrant_collection_name", "arxiv_llms")
        self.host = qdrant_config.get("qdrant_host", "localhost")
        self.port = qdrant_config.get("qdrant_port", 6333)
        self.embedding_model_path = qdrant_config.get("embedding_model_path", "")
        self.device = qdrant_config.get("device", "cpu")

        # Initialize the embedding model
        if not self.embedding_model_path:
            raise ValueError("embedding_model_path must be provided in config")

        self.embedding_generator = SentenceTransformerEmbedding(
            model_name_or_path=self.embedding_model_path,
            device=self.device
        )

        # Initialize Qdrant engine
        self.engine = QdrantEngine(
            collection_name=self.collection_name,
            embedding_generator=self.embedding_generator,
            qdrant_client_params={"host": self.host, "port": self.port},
            vector_size=self.embedding_generator.embedding_size
        )

        # Initialize HTTP client for any additional API requests
        self.client = httpx.Client(timeout=30.0)

    def search_sync(self, query: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform a synchronous search using Qdrant.

        Args:
            query: Search query
            options: Additional options for the search

        Returns:
            Dict containing search results
        """
        if options is None:
            options = {}

        limit = options.get("limit", 5)

        # Handle filter conditions if provided
        query_filter = None
        if "filter_conditions" in options:
            query_filter = self._build_filter(options["filter_conditions"])

        try:
            logger.debug(f"Searching with Qdrant: {query}")
            search_results = self.engine.search(
                text=query,
                query_filter=query_filter,
                limit=limit
            )

            # Transform the result to match the expected format
            transformed_result = self._transform_result(search_results, query)
            logger.debug(f"Transformed result: {transformed_result}")
            return transformed_result

        except Exception as e:
            logger.error(f"Error searching with Qdrant: {str(e)}")
            raise

    async def search(self, query: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform an async search using Qdrant.

        Note: This method runs the synchronous method in a separate thread
        as the Qdrant client doesn't natively support async operations.

        Args:
            query: Search query
            options: Additional options for the search

        Returns:
            Dict containing search results
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        # Create a thread pool and run the synchronous search in it
        with ThreadPoolExecutor() as executor:
            result = await asyncio.get_event_loop().run_in_executor(
                executor,
                self.search_sync,
                query,
                options
            )

        return result

    def _build_filter(self, conditions: List[Dict[str, Any]]) -> Filter:
        """
        Build a Qdrant filter from a list of conditions.

        Args:
            conditions: A list of conditions, where each condition is a dictionary with:
                      - key: The field name to filter on.
                      - match: The value to match.

        Returns:
            A Qdrant Filter object.
        """
        filter_conditions = []
        for condition in conditions:
            key = condition.get("key")
            match_value = condition.get("match")
            if key and match_value is not None:
                filter_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=match_value),
                    )
                )

        return Filter(must=filter_conditions)

    def _transform_result(self, qdrant_results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """
        Transform Qdrant search results to match the expected format.

        Args:
            qdrant_results: Raw results from Qdrant search
            query: Original search query

        Returns:
            Transformed result in compatible format
        """
        transformed_data = []
        logger.debug(f"Transforming Qdrant search result: {qdrant_results}")

        try:
            for item in qdrant_results:
                payload = item.get("payload", {})
                score = item.get("score", 0.0)

                transformed_item = {
                    "url": payload.get("url", ""),
                    "title": payload.get("title", ""),
                    "content": payload.get("content", "")[:4000],  # Limit content to 4000 chars
                    "source": "qdrant_search",
                    "score": score
                }
                transformed_data.append(transformed_item)

        except Exception as e:
            logger.error(f"Error transforming Qdrant result: {str(e)}")
            # Add a fallback item with the error
            transformed_item = {
                "url": "",
                "title": "Qdrant Search Error",
                "content": f"Error processing result: {str(e)}\nRaw result: {qdrant_results}",
                "source": "qdrant_search"
            }
            transformed_data.append(transformed_item)

        return {
            "query": query,
            "data": transformed_data
        }
