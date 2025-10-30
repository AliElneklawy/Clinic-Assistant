import asyncio
import uuid

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_cohere import ChatCohere
from langchain_tavily import TavilySearch
from langchain.tools import Tool

from agents.base_agent import BaseAgent
from rag.cohere_rag import CohereRAG
from scripts import get_api_key
from settings import prompts
from settings.logger import get_logger


logger = get_logger(__name__)


class QueryHandlerAgent(BaseAgent):
    def __init__(self,
                 content_path,
                 index_path,
                 rerank: bool = True,
                 max_search_results: int = 3):
        self.max_results = max_search_results
        self.llm = ChatCohere(cohere_api_key=get_api_key.get_key("COHERE"))

        logger.info("Initializing RAG system...")
        self.rag = CohereRAG(content_path=content_path,
                             index_path=index_path, 
                             rerank=rerank)
        
        super().__init__()
    
    def _init_prompt(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                {
                    "role": "system",
                    "content": prompts.QUERY_HANDLER_PROMPT
                },
                {
                    "role": "human",
                    "content": "{query}"
                },
                {
                    "role": "placeholder", 
                    "content": "{agent_scratchpad}"
                }
            ]
        )

        return prompt
    
    def _init_tools(self):
        self.tools = [
            Tool(
                name = "search_clinic_database",
                func=self._search_clinic_database,
                description=(
                    "Use the existing RAG system to search the clinic's internal knowledge base. "
                    "Use this FIRST for any medical queries. "
                )
            ),
            TavilySearch(
                tavily_api_key=get_api_key.get_key("TAVILY_SEARCH"),
                max_results=self.max_results,
                search_depth="advanced",
                include_answer=True,
                include_raw_content=False,
                description=(
                    "Search the web for medical information when the clinic database "
                    "doesn't have sufficient information. Use this as a secondary source. "
                )
            )
        ]

    def _init_agent(self):
        self.agent = create_tool_calling_agent(
            llm=self.llm, 
            tools=self.tools, 
            prompt=self.prompt
        )

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True
        )

    def _search_clinic_database(self, query: str) -> str:
        """
        Search the clinic database using RAG system.
        
        Args:
            query: The search query from the user
            
        Returns:
            Response from the RAG system
        """
        try:
            logger.info(f"Searching clinic database for: {query}")
            
            # Run the async method synchronously
            response = asyncio.run(
                self.rag.get_response(
                    query=query,
                    user_id=uuid.uuid4()
                )
            )
            
            logger.info("Successfully retrieved response from clinic database")
            return response
        except Exception as e:
            logger.error(f"Error searching clinic database: {e}")
            return f"Unable to search clinic database. Error: {str(e)}"
        
    def run(self, query: str):
        result = self.agent_executor.invoke({"query": query})
        return result


if __name__ == "__main__":
    agent = QueryHandlerAgent()
    result = agent.run("I have a really bad headache. What should I do?")

    print(result)
