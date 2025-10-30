import cohere

from embeddings.base_embedding import BaseEmbedding
from scripts import get_api_key
from settings.logger import get_logger

logger = get_logger(__name__)


class CohereEmbedding(BaseEmbedding):
    def __init__(self, embedding_model: str = "embed-multilingual-v3.0"):
        self.client = cohere.Client(get_api_key.get_key("COHERE"))
        self.embedding_model = embedding_model

        logger.info(f"Using cohere's {embedding_model} embedding model.")

    def embed(self, texts: list | str, is_query: bool) -> list:
        input_type = "search_query" if is_query else "search_document"
        return self.client.embed(
            texts=texts,
            model=self.embedding_model,
            input_type=input_type,
        ).embeddings
