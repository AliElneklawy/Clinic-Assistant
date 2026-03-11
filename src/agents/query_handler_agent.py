import os

from langchain.agents import (
    AgentExecutor,
    create_react_agent,
)
from langchain.schema import HumanMessage
from langchain.tools import Tool
from langchain_cohere import ChatCohere
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import CohereTextVectorizer

from src.agents.base_agent import BaseAgent
from src.container import create_agent_tools
from src.scripts import create_folder, get_api_key
from src.settings import agent_config, cache_config, prompts
from src.settings.logger import get_logger
from src.settings.paths import DATA_DIR
from src.services.cache.redis_service import RedisService

logger = get_logger(__name__)


class QueryHandlerAgent(BaseAgent):
    def __init__(self):
        """
        Initialize the QueryHandlerAgent with RAG system and LLM.
        """
        self.db_path = create_folder.create(DATA_DIR / "database") / "chat_history.db"

        logger.info("Initializing LLM...")
        self.llm = ChatCohere(cohere_api_key=get_api_key.get_key("COHERE"))

        logger.info("Initializing tools...")
        self.agent_tools = create_agent_tools()  # AgentTools(rag=self.rag)

        logger.info("Initializing Redis cache...")
        self.cache = RedisService(name="MediCare_AI")

        super().__init__()

    def _init_prompt(self):
        """Initialize the prompt template for the ReAct agent."""
        prompt = PromptTemplate(
            template=prompts.ReAct_FRAMEWORK,
            input_variables=["input", "agent_scratchpad", "history"],
            partial_variables={
                "system_prompt": prompts.QUERY_HANDLER_PROMPT,
            },
        )

        return prompt

    def _init_tools(self):
        """
        Initialize the tools available to the agent.
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
                    "Pass the data in the follownig example string format (ALL FIELDS REQUIRED. ALWAYS ASK THE USER FOR MISSING FIELDS): \n"
                    "date_str='November 03, 2025', time_str='01:40 PM', user_id='xxxxxx', patient_name='Ali', patient_age=25, description='Test', patient_email=test@example.com"
                ),
            ),
            Tool(
                func=self.agent_tools.cancel_appointment,
                name="cancel_appointment",
                description=(
                    "Cancel an appointment from Google Calendar. "
                    "Pass the event ID as a string. Example: '129mqpqtkk8p0oadicc0o5fm2o'"
                ),
            ),
            Tool(
                func=self.agent_tools.classify_diabetes,
                name="classify_diabetes",
                description=(
                    "Classify a patient's diabetes based on various factors. "
                    "Always mention the probability of being diabetic and the final diagnosis. "
                    "The following fields are MANDATORY: gender, age, hypertension, heart_disease, smoking_history, bmi, HbA1c_level, blood_glucose_level. "
                    "If any of the fields is missing, ask the user to provide it. "
                    "Pass the data in the follownig example string format: \n"
                    "gender='Male', age=30, hypertension='yes', heart_disease='no', smoking_history='never', bmi=25.0, HbA1c_level=5.5, blood_glucose_level=120"
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

        self.agent_with_history = RunnableWithMessageHistory(
            self.agent_executor,
            self.get_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def get_history(self, user_id: str):
        return SQLChatMessageHistory(
            connection=f"sqlite:///{self.db_path}",
            table_name="messages",
            session_id=user_id,
        )

    def run(self, query: str, user_id: str):
        """
        Execute the agent with a given query.

        Args:
            query: The user's query to process

        Returns:
            The agent's response after processing the query and using available tools
        """
        if response := self.cache.retrieve(key=query):
            logger.info("Cache hit. Responding from cache...")
            return response[0]["response"]

        logger.info("Cache miss. Invoking LLM...")
        query_with_id = f"[User ID: {user_id}]\n{query}"

        h = self.get_history(user_id)
        last_n_messages = "\n".join(
            f"{'Human' if isinstance(msg, HumanMessage) else 'AI'}: {msg.content}"
            for msg in h.messages[-agent_config.LAST_N_MESSAGES :]
        )

        result = self.agent_with_history.invoke(
            {"input": query_with_id, "history": last_n_messages},
            config={"configurable": {"session_id": user_id}},
        )

        self.cache.store(key=query, value=result["output"])

        return result["output"]


if __name__ == "__main__":
    agent = QueryHandlerAgent()
    result = agent.run("How can I treat my headache?", "test_user_id2")

    print(result)


# Regarding the initialization process of the vectorizer. I kept getting the following errors:
#   1. TypeError: Must pass in a str value for cohere embedding input_type. See https://docs.cohere.com/reference/embed
#   2. TypeError: Client.__init__() got an unexpected keyword argument 'input_type'
# The second error occured when I tried to pass the 'input_type' arg CohereTextVectorizer.
# So I had to change line 236 from
#                               `input_type = kwargs.pop("input_type", None)`
#                             to
#                               `input_type = kwargs.pop("input_type", "search_query")`
# in .venv\Lib\site-packages\redisvl\utils\vectorize\text\cohere.py
