import cohere

from rag.base_rag import BaseRAG
from scripts import get_api_key
from settings import rag_config

# from embeddings.cohere_embedding import CohereEmbedding
from settings.logger import get_logger

logger = get_logger(__name__)


class CohereRAG(BaseRAG):
    def _initialize_models(self, model_name: str = None):
        config = rag_config.CohereConfig()
        api = get_api_key.get_key("COHERE")
        self.cohere_client = cohere.AsyncClientV2(api)
        self.cohere_model = model_name or next(
            iter(config.AVAILABLE_MODELS)
        )  # get the first model in the list
        self.in_price, self.out_price = config.AVAILABLE_MODELS[self.cohere_model]
        # self.embedding_provider = CohereEmbedding()

        logger.info(f"Using Cohere's model {self.cohere_model}.")

    async def get_response(self, query: str, user_id: str) -> str:
        """Get response using Cohere."""
        context = self._find_relevant_context(query)
        # print(context)
        # exit()
        # return context if context else "No information found."
        system_prompt = self._generate_system_prompt(query, user_id, context)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        try:
            response = await self.cohere_client.chat(
                model=self.cohere_model,
                messages=messages,
                max_tokens=rag_config.MAX_OUT_TOKENS,
                temperature=rag_config.TEMPERATURE,
            )
            response_text = response.message.content[0].text.strip()

        except Exception as e:
            logger.error(f"Error getting Cohere response: {e}")
            return "I'm sorry, I couldn't process your request at the moment."

        return response_text
    
    async def get_response_with_sources(self, query: str, user_id: str) -> dict:
        """Get response using Cohere with source citations."""
        context, sources = self._find_relevant_context_with_sources(query)
        
        if not context:
            return {
                "response": "No information found in the database.",
                "sources": []
            }
        
        system_prompt = self._generate_system_prompt(query, user_id, context)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        try:
            response = await self.cohere_client.chat(
                model=self.cohere_model,
                messages=messages,
                max_tokens=rag_config.MAX_OUT_TOKENS,
                temperature=rag_config.TEMPERATURE,
            )
            response_text = response.message.content[0].text.strip()

        except Exception as e:
            logger.error(f"Error getting Cohere response: {e}")
            return {
                "response": "I'm sorry, I couldn't process your request at the moment.",
                "sources": []
            }

        return {
            "response": response_text,
            "sources": sources
        }
