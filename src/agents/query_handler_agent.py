import asyncio
from functools import lru_cache
import uuid

from langchain.agents import AgentExecutor, create_tool_calling_agent, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_cohere import ChatCohere
from langchain_core.prompts import ChatPromptTemplate
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

    # def _init_prompt(self) -> ChatPromptTemplate:
    #     """
    #     Initialize the prompt template for the agent.

    #     Returns:
    #         ChatPromptTemplate: The configured prompt template with system, human, and scratchpad messages
    #     """
    #     prompt = ChatPromptTemplate.from_messages(
    #         [
    #             {"role": "system", "content": prompts.QUERY_HANDLER_PROMPT},
    #             {"role": "human", "content": "{query}"},
    #             {"role": "placeholder", "content": "{agent_scratchpad}"},
    #         ]
    #     )

    #     return prompt

    def _init_prompt(self):
        """Initialize the prompt template for the ReAct agent."""
        
        # template = """
        #     {system_prompt}

        #     You have access to the following tools:

        #     {tools}

        #     Use the following format:

        #     Question: the input question you must answer
        #     Thought: you should always think about what to do
        #     Action: the action to take, should be one of [{tool_names}]
        #     Action Input: the input to the action
        #     Observation: the result of the action
        #     ... (this Thought/Action/Action Input/Observation can repeat N times)
        #     Thought: I now know the final answer
        #     Final Answer: the final answer to the original input question

        #     IMPORTANT: 
        #     - Call each tool EXACTLY ONCE per query
        #     - Check your previous actions before deciding to act
        #     - If you've already called a tool, DO NOT call it again

        #     Begin!

        #     Question: {input}
        #     Thought: {agent_scratchpad}
    # """

        prompt = PromptTemplate(
            template=prompts.ReAct_FRAMEWORK,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "system_prompt": prompts.QUERY_HANDLER_PROMPT,
            }
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
                    "Use the existing RAG system to search the clinic's internal knowledge base. "
                    "ALWAYS call this FIRST for any medical queries. Returns the database response that "
                    "you must evaluate to determine if web search is needed."
                ),
            ),
            Tool(
                name="search_web",
                func=self._search_web,
                description=(
                    "Search the web for current, up-to-date medical information. MUST use this when: "
                    "1) Clinic database has no information, 2) Query asks about recent/current events, "
                    "specific dates, new drugs/treatments, 3) Database provides incomplete information. "
                    "Returns search results with URLs as references."
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
            max_iterations=10,  # Allow enough iterations for database + web search + reasoning
            early_stopping_method="generate",  # Stop when a final answer is generated
            handle_parsing_errors=True,  # Handle any parsing errors gracefully
        )

    @lru_cache()
    def _search_clinic_database(self, query: str) -> str:
        """
        Search the clinic database using RAG system.

        Args:
            query: The search query from the user

        Returns:
            Response from the RAG system with source citations
        """
        try:
            logger.info(f"Searching clinic database for: {query}")

            # Get or create a new event loop to avoid "Event loop is closed" errors
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async method synchronously with sources
            result = loop.run_until_complete(
                self.rag.get_response_with_sources(query=query, user_id=uuid.uuid4())
            )

            response_text = result.get("response", "")
            sources = result.get("sources", [])
            
            # Format the response with sources
            formatted_response = f"Database Response:\n{response_text}"
            
            if sources:
                formatted_response += "\n\nSources from Database:\n"
                for idx, source in enumerate(sources, 1):
                    # Get a preview of the text (first 200 characters)
                    text_preview = source.get("text", "")[:200]
                    if len(source.get("text", "")) > 200:
                        text_preview += "..."
                    
                    formatted_response += f"\n[Source {idx}]\n"
                    formatted_response += f"Excerpt: {text_preview}\n"
                    
                    # Add relevance score if available (from reranking)
                    if "relevance_score" in source:
                        formatted_response += f"Relevance Score: {source['relevance_score']:.3f}\n"

            logger.info("Successfully retrieved response from clinic database with sources")
            return formatted_response
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
                        content = result.get('content', '')
                        url = result.get('url', '')
                        
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
