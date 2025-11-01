import asyncio
import datetime
import uuid
from functools import lru_cache
from typing import List, Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_tavily import TavilySearch

from rag.cohere_rag import CohereRAG
from scripts import get_api_key
from scripts.auth_calendar import authenticate_calendar
from settings import agent_config, clinic_config
from settings.logger import get_logger

logger = get_logger(__name__)


class AgentTools:
    def __init__(self, rag: CohereRAG):
        self.rag = rag

        self.tavily_search = TavilySearch(
            tavily_api_key=get_api_key.get_key("TAVILY_SEARCH"),
            max_results=agent_config.MAX_SEARCH_RESULTS,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
        )

        logger.info("Authenticating google calendar API...")
        # creds = authenticate_calendar()
        self.service = build("calendar", "v3", credentials=authenticate_calendar())

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
            web_results = self.search_web(query)

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
    def search_clinic_database(self, query: str) -> str:
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

    def search_web(self, query: str) -> str:
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

    def _is_slot_available(
        self,
        slot_start: datetime.datetime,
        slot_end: datetime.datetime,
        busy_times: List[dict],
    ) -> bool:
        """Check if a time slot conflicts with any existing events."""
        for event in busy_times:
            event_start = datetime.datetime.fromisoformat(
                event["start"].get("dateTime", event["start"].get("date"))
            )
            event_end = datetime.datetime.fromisoformat(
                event["end"].get("dateTime", event["end"].get("date"))
            )

            if event_start.tzinfo:
                event_start = event_start.replace(tzinfo=None)
            if event_end.tzinfo:
                event_end = event_end.replace(tzinfo=None)

            # Check for overlap
            if not (slot_end <= event_start or slot_start >= event_end):
                return False

        return True

    def _generate_time_slots(
        self, date: datetime.date
    ) -> List[Tuple[datetime.datetime, datetime.datetime]]:
        """Generate all possible time slots for a given day."""
        slots = []
        current_time = datetime.datetime.combine(
            date, datetime.time(clinic_config.WORK_START_HOUR, 0)
        )
        end_time = datetime.datetime.combine(
            date, datetime.time(clinic_config.WORK_END_HOUR, 0)
        )

        while current_time < end_time:
            slot_end = current_time + datetime.timedelta(
                minutes=clinic_config.SLOT_DURATION_MINUTES
            )

            if clinic_config.ENABLE_LUNCH_BREAK:
                slot_time = current_time.time()
                if (
                    clinic_config.LUNCH_BREAK_START
                    <= slot_time
                    < clinic_config.LUNCH_BREAK_END
                ):
                    current_time = slot_end
                    continue

            slots.append((current_time, slot_end))

            current_time = slot_end + datetime.timedelta(
                minutes=clinic_config.BUFFER_TIME_MINUTES
            )

        return slots

    def list_available_slots(self, _="") -> str:
        """
        List all available appointments from google calendar.
        Use this to find the next available appointment times starting today
        and excluding weekends.
        """
        slots: dict = {}

        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=clinic_config.DAYS_TO_SHOW)

        time_min = (
            datetime.datetime.combine(today, datetime.time(0, 0)).isoformat() + "Z"
        )
        time_max = (
            datetime.datetime.combine(end_date, datetime.time(23, 59)).isoformat() + "Z"
        )

        events_result = (
            self.service.events()
            .list(
                calendarId=clinic_config.CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        existing_events = events_result.get("items", [])
        for day_offset in range(clinic_config.DAYS_TO_SHOW):
            current_date = today + datetime.timedelta(days=day_offset)

            if clinic_config.SKIP_WEEKENDS and current_date.weekday() >= 5:
                continue

            day_slots = self._generate_time_slots(current_date)
            available = []

            for slot_start, slot_end in day_slots:
                if self._is_slot_available(slot_start, slot_end, existing_events):
                    available.append(
                        f"{slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}"
                    )

            if available:
                slots[current_date.strftime("%A, %B %d, %Y")] = available

        return slots
