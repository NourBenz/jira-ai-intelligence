"""Local Ollama embedding client for RAG indexing and retrieval."""

import json

import requests
from fastapi import HTTPException


class OllamaEmbeddingClient:
    """Generate embeddings without sending Jira text to a cloud provider."""

    def __init__(
        self,
        base_url: str,
        model: str = "nomic-embed-text",
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a prepared non-empty batch and validate Ollama's response shape."""
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("Embedding input must not contain empty text.")

        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            embeddings = payload["embeddings"]
            if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                raise ValueError("Embedding count does not match input count.")

            normalized = [[float(value) for value in vector] for vector in embeddings]
            dimensions = {len(vector) for vector in normalized}
            if not normalized or dimensions == {0} or len(dimensions) != 1:
                raise ValueError("Embedding vectors have invalid dimensions.")
            return normalized
        except requests.exceptions.Timeout as error:
            raise HTTPException(504, "The local embedding model timed out.") from error
        except requests.exceptions.ConnectionError as error:
            raise HTTPException(503, "The local embedding service is unavailable.") from error
        except (
            requests.exceptions.RequestException,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise HTTPException(
                502, "The local embedding model returned an invalid response."
            ) from error

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """Embed RAG documents using Nomic's required retrieval instruction."""
        return self._embed([f"search_document: {document}" for document in documents])

    def embed_query(self, query: str) -> list[float]:
        """Embed one query using Nomic's required retrieval instruction."""
        return self._embed([f"search_query: {query}"])[0]
