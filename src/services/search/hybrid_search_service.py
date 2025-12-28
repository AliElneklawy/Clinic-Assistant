from scripts.response_formatter import format_response_with_sources
from services.search.database_search_service import DatabaseSearchService
from services.search.web_search_service import WebSearchService
from settings import agent_config
from settings.logger import get_logger

logger = get_logger(__name__)


class HybridSearchService:
    def __init__(
        self, db_service: DatabaseSearchService, web_service: WebSearchService
    ) -> None:
        self.db_service = db_service
        self.web_service = web_service

    def search(self, query: str) -> str:
        """
        Search database and automatically call web search if relevance is low.
        This is a helper that combines both tools intelligently.
        """
        db_result = self.db_service.search(query)

        response_text = db_result.get("response", "")
        sources = db_result.get("sources", [])
        max_relevance = db_result.get("max_relevance_score", 1.0)
        has_scores = db_result.get("has_relevance_scores", False)

        needs_web_search = (
            has_scores and max_relevance < agent_config.RELEVANCE_THRESHOLD
        )

        if needs_web_search:
            logger.info(
                f"Low relevance score ({max_relevance:.3f}), triggering web search"
            )
            web_results = self.web_service.search(query)

            combined = f"{response_text}\n\n---\n\nAdditional Web Search (triggered due to low relevance score {max_relevance:.3f}):\n{web_results}"
            return format_response_with_sources(
                combined, sources, max_relevance, has_scores
            )

        return format_response_with_sources(
            response_text, sources, max_relevance, has_scores
        )
