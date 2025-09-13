from abc import ABC, abstractmethod


class BaseEmbedding(ABC):
    @abstractmethod
    def embed(self, texts: list) -> list:
        """
        Generate embeddings for a list of texts.

        Args:
            texts (List[str]): List of texts to embed.

        Returns:
            List[List[float]]: List of embedding vectors.
        """
        pass

    def embed_documents(self, text: str):
        """This method is used as a wrapper for langchain's semantic chunker."""
        return self.embed(text, False)
