from langchain.agents import (
    AgentExecutor,
    create_react_agent,
)
from langchain.tools import Tool
from langchain_cohere import ChatCohere
from langchain_core.prompts import PromptTemplate
from langchain_tavily import TavilySearch

from agents.base_agent import BaseAgent
from agents.tools import AgentTools
from rag.cohere_rag import CohereRAG
from scripts import get_api_key
from settings import agent_config
from settings import prompts
from settings.logger import get_logger

logger = get_logger(__name__)


class QueryHandlerAgent(BaseAgent):
    def __init__(
        self, content_path, index_path, rerank: bool = True
    ):
        """
        Initialize the QueryHandlerAgent with RAG system and LLM.

        Args:
            content_path: Path to the content directory for the RAG system
            index_path: Path to the index directory for the RAG system
            rerank: Whether to enable reranking in the RAG system (default: True)
            max_search_results: Maximum number of search results to retrieve (default: 3)
        """
        self.llm = ChatCohere(
            cohere_api_key=get_api_key.get_key("COHERE"),
        )
        self.tavily_search = TavilySearch(
            tavily_api_key=get_api_key.get_key("TAVILY_SEARCH"),
            max_results=agent_config.MAX_SEARCH_RESULTS,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
        )

        logger.info("Initializing RAG system...")
        self.rag = CohereRAG(
            content_path=content_path, index_path=index_path, rerank=rerank
        )

        logger.info("Initializing tools...")
        self.agent_tools = AgentTools(rag=self.rag, tavily_search=self.tavily_search)

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
                func=self.agent_tools._search_clinic_database,
                description=(
                    "Search the clinic's knowledge base. Automatically triggers web search if "
                    f"relevance score is below {agent_config.RELEVANCE_THRESHOLD}. Use this for all medical queries. "
                    "Knowledge in the databse is limited at 2023."
                ),
            ),
            Tool(
                name="search_web",
                func=self.agent_tools._search_web,
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
