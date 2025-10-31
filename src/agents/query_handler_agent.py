import asyncio
import uuid
from functools import lru_cache

from langchain.agents import (
    AgentExecutor,
    create_react_agent,
)
from langchain.tools import Tool
from langchain_cohere import ChatCohere
from langchain_core.prompts import PromptTemplate
from langchain_tavily import TavilySearch

from agents.base_agent import BaseAgent
from rag.cohere_rag import CohereRAG
from scripts import get_api_key
from settings import prompts
from settings.logger import get_logger

logger = get_logger(__name__)


class QueryHandlerAgent(BaseAgent):
    def __init__(
        self, content_path, index_path, rerank: bool = True, max_search_results: int = 3
    ):
        """
        Initialize the QueryHandlerAgent with RAG system and LLM.

        Args:
            content_path: Path to the content directory for the RAG system
            index_path: Path to the index directory for the RAG system
            rerank: Whether to enable reranking in the RAG system (default: True)
            max_search_results: Maximum number of search results to retrieve (default: 3)
        """
        self.max_results = max_search_results
        self.llm = ChatCohere(
            cohere_api_key=get_api_key.get_key("COHERE"),
        )

        self.tavily_search = TavilySearch(
            tavily_api_key=get_api_key.get_key("TAVILY_SEARCH"),
            max_results=self.max_results,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
        )

        logger.info("Initializing RAG system...")
        self.rag = CohereRAG(
            content_path=content_path, index_path=index_path, rerank=rerank
        )

        super().__init__()

    def _init_prompt(self):
        """Initialize the prompt template for the ReAct agent."""
        prompt = PromptTemplate(
            template=prompts.ReAct_FRAMEWORK,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "system_prompt": prompts.QUERY_HANDLER_PROMPT,
            },
        )

        return prompt

    def _init_tools(self):
        """
        Initialize the tools available to the agent.

        Creates two tools:
        1. search_clinic_database: Searches the internal clinic knowledge base using RAG
        2. search_web: Searches the web for additional medical information with URL references
        """
        self.tools = [
            Tool(
                name="search_clinic_database",
                func=self._search_clinic_database,
                description=(
                    "Search the clinic's knowledge base. Automatically triggers web search if "
                    "relevance score is below 0.6 (60%). Use this for all medical queries."
                ),
            ),
            Tool(
                name="search_web",
                func=self._search_web,
                description=(
                    "Search the web for current medical information. Only use if you need "
                    "additional recent/specific information not covered by the database search."
                ),
            ),
        ]

    def _init_agent(self):
        """
        Initialize the agent and agent executor.

        Creates a tool-calling agent with the configured LLM, tools, and prompt,
        then wraps it in an AgentExecutor for execution.
        """
        self.agent = create_react_agent(
            llm=self.llm, tools=self.tools, prompt=self.prompt
        )

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            early_stopping_method="generate",
            handle_parsing_errors=True,
        )

    def _check_relevance_and_search(self, query: str) -> str:
        """
        Search database and automatically call web search if relevance is low.
        This is a helper that combines both tools intelligently.
        """
        db_result = self._search_clinic_database_internal(query)

        response_text = db_result.get("response", "")
        sources = db_result.get("sources", [])
        max_relevance = db_result.get("max_relevance_score", 1.0)
        has_scores = db_result.get("has_relevance_scores", False)

        needs_web_search = has_scores and max_relevance < 0.6

        if needs_web_search:
            logger.info(
                f"Low relevance score ({max_relevance:.3f}), triggering web search"
            )
            web_results = self._search_web(query)

            combined = f"{response_text}\n\n---\n\nAdditional Web Search (triggered due to low relevance score {max_relevance:.3f}):\n{web_results}"
            return self._format_response_with_sources(
                combined, sources, max_relevance, has_scores
            )

        return self._format_response_with_sources(
            response_text, sources, max_relevance, has_scores
        )

    def _search_clinic_database_internal(self, query: str) -> dict:
        """Internal method to search database and return structured data."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            self.rag.get_response_with_sources(query=query, user_id=uuid.uuid4())
        )

        sources = result.get("sources", [])
        max_relevance_score = 0.0
        has_relevance_scores = False

        for source in sources:
            if "relevance_score" in source:
                has_relevance_scores = True
                max_relevance_score = max(
                    max_relevance_score, source["relevance_score"]
                )

        return {
            "response": result.get("response", ""),
            "sources": sources,
            "max_relevance_score": max_relevance_score,
            "has_relevance_scores": has_relevance_scores,
        }

    def _format_response_with_sources(
        self, response_text: str, sources: list, max_relevance: float, has_scores: bool
    ) -> str:
        """Format response with concise source citations."""
        formatted = f"{response_text}"

        if sources:
            formatted += "\n\nSources:"
            for idx, source in enumerate(sources, 1):
                text_preview = source.get("text", "")[:150]
                if len(source.get("text", "")) > 150:
                    text_preview += "..."
                formatted += f"\n[{idx}] {text_preview}"
                if "relevance_score" in source:
                    formatted += f" (score: {source['relevance_score']:.2f})"

        return formatted

    @lru_cache()
    def _search_clinic_database(self, query: str) -> str:
        """
        Search the clinic database using RAG system.
        Automatically triggers web search if relevance score is below 0.6.
        """
        try:
            logger.info(f"Searching clinic database for: {query}")
            result = self._check_relevance_and_search(query)
            logger.info("Successfully retrieved response from clinic database")
            return result
        except Exception as e:
            logger.error(f"Error searching clinic database: {e}")
            return f"Unable to search clinic database. Error: {str(e)}"

    def _search_web(self, query: str) -> str:
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

    def run(self, query: str):
        """
        Execute the agent with a given query.

        Args:
            query: The user's query to process

        Returns:
            The agent's response after processing the query and using available tools
        """
        result = self.agent_executor.invoke({"input": query})
        return result


if __name__ == "__main__":
    agent = QueryHandlerAgent()
    result = agent.run("I have a really bad headache. What should I do?")

    print(result)
