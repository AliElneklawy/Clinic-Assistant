from langchain.agents import (
    AgentExecutor,
    create_openai_tools_agent,
    create_react_agent,
)
from langchain.memory import ChatMessageHistory
from langchain.tools import StructuredTool, Tool
from langchain_cohere import ChatCohere
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.runnables.history import RunnableWithMessageHistory

from agents.base_agent import BaseAgent
from agents.tools import AgentTools
from models.appointment import BookAppointmentInput
from rag.cohere_rag import CohereRAG
from scripts import get_api_key
from settings import agent_config, prompts
from settings.logger import get_logger

logger = get_logger(__name__)


class QueryHandlerAgent(BaseAgent):
    def __init__(self, content_path, index_path, rerank: bool = True):
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

        logger.info("Initializing RAG system...")
        self.rag = CohereRAG(
            content_path=content_path, index_path=index_path, rerank=rerank
        )

        logger.info("Initializing tools...")
        self.agent_tools = AgentTools(rag=self.rag)

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

        # prompt = ChatPromptTemplate.from_messages([
        #     ("system", prompts.QUERY_HANDLER_PROMPT),
        #     ("human", "{input}"),
        #     MessagesPlaceholder(variable_name="agent_scratchpad"),
        # ])
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
                func=self.agent_tools.search_clinic_database,
                description=(
                    "Search the clinic's knowledge base. Automatically triggers web search if "
                    f"relevance score is below {agent_config.RELEVANCE_THRESHOLD}. Use this for all medical queries. "
                    "Knowledge in the databse is limited at 2023."
                ),
            ),
            Tool(
                name="search_web",
                func=self.agent_tools.search_web,
                description=(
                    "Search the web for current medical information. Only use if you need "
                    "additional recent/specific information not covered by the database search."
                ),
            ),
            Tool(
                name="list_available_slots",
                func=self.agent_tools.list_available_slots,
                description=(
                    "List all available appointments from goolge calendar. "
                    "Use this to find the next available appointment times starting today. "
                    "If a specific day is NOT shown in the output, it means the doctor is NOT available on that day."
                ),
            ),
            Tool(
                func=self.agent_tools.book_appointment,
                name="book_appointment",
                description=(
                    "Book an appointment on Google Calendar. "
                    "Make sure that the appointment is available before booking by calling list_available_slots first."
                    "Pass the data in the follownig example string format: \n"
                    "date_str='November 03, 2025', time_str='01:40 PM', patient_name=None, patient_age=None, description=None, patient_email=None"
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
