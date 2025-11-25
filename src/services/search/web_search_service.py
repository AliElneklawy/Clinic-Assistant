from langchain_tavily import TavilySearch

from settings.logger import get_logger

logger = get_logger(__name__)


class WebSearchService:
    def __init__(self, tavily_search: TavilySearch) -> None:
        self.tavily_search = tavily_search

    def search(self, query: str) -> str:
        """
        Search the web using Tavily and format results with URLs as references.

        Args:
            query: The search query from the user

        Returns:
            Formatted response with content and URL references
        """
        try:
            logger.info(f"Searching web for: {query}")

            results = self.tavily_search.invoke(query)

            if isinstance(results, list) and len(results) > 0:
                formatted_response = "Web Search Results:\n\n"

                for idx, result in enumerate(results, 1):
                    if isinstance(result, dict):
                        content = result.get("content", "")
                        url = result.get("url", "")

                        if content:
                            formatted_response += f"{idx}. {content}\n"
                        if url:
                            formatted_response += f"   Source: {url}\n\n"

                logger.info("Successfully retrieved web search results with URLs")
                return formatted_response
            else:
                return f"Web search results: {results}"

        except Exception as e:
            logger.error(f"Error searching web: {e}")
            return f"Unable to search web. Error: {str(e)}"
