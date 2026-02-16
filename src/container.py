"""
Builds and returns the `AgentTools` instance used by the agent.

This function wires together:
- A RAG system for local medical information retrieval.
- Google Calendar services (authentication, event building, slot management).
- Hybrid search (Tavily web search + local RAG database search).
- A diabetes classification model loaded via joblib.

All services are initialized and packaged into a single `AgentTools` object,
which the agent uses to perform calendar operations, search queries, and ML-based
diabetes prediction.
"""

import joblib
from dotenv import load_dotenv
from googleapiclient.discovery import build
from langchain_tavily import TavilySearch

from src.rag.rag_system import RAGSystem
from src.scripts import get_api_key
from src.scripts.auth_calendar import authenticate_calendar
from src.services.calendar.calendar_service import CalendarService
from src.services.calendar.event_builder import EventBuilder
from src.services.calendar.slot_manager import SlotManager
from src.services.database.database_service import DatabaseOpsService
from src.services.email.email_service import EmailService
from src.services.ml.classify_diabetes import ClassifyDiabetesService
from src.services.search.database_search_service import DatabaseSearchService
from src.services.search.hybrid_search_service import HybridSearchService
from src.services.search.web_search_service import WebSearchService
from src.settings import agent_config
from src.settings.paths import DIABETES_MODEL_PATH, INDEXES_DIR, MED_DATA_FILE
from src.agents.tools import AgentTools

load_dotenv()


def create_agent_tools():
    rag = RAGSystem(
        content_path=MED_DATA_FILE,
        index_path=INDEXES_DIR,  # / "index_7ad274e90429ac4.faiss.temp" / "index_6c65bfa3c607d34.faiss",
    )

    # Database services
    db_service = DatabaseOpsService()

    # Calendar services
    event_builder = EventBuilder()
    slot_manager = SlotManager()
    calendar_service = CalendarService(
        event_builder=event_builder,
        slot_manager=slot_manager,
        db=db_service,
        service=build("calendar", "v3", credentials=authenticate_calendar()),
    )

    # Search services
    tavily_search = TavilySearch(
        tavily_api_key=get_api_key.get_key("TAVILY_SEARCH"),
        max_results=agent_config.MAX_SEARCH_RESULTS,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
    )
    web_search = WebSearchService(tavily_search)
    db_search = DatabaseSearchService(rag)
    hyprid_search_service = HybridSearchService(db_search, web_search)

    # ML services
    classify_diabetes_service = ClassifyDiabetesService(
        model=joblib.load(DIABETES_MODEL_PATH)
    )

    # Email services
    email_service = EmailService(
        sender_email=get_api_key.get_key("SENDER_EMAIL"),
        app_password=get_api_key.get_key("GMAIL_APP_PASSWORD"),
        db=db_service,
    )

    return AgentTools(
        calendar_service=calendar_service,
        search_service=hyprid_search_service,
        diabetes_classifier_service=classify_diabetes_service,
        email_service=email_service,
    )
