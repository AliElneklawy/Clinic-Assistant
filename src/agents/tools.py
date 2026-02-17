from typing import TypeVar

from pydantic import BaseModel

from src.settings.logger import get_logger
from src.services.calendar.calendar_service import CalendarService
from src.services.email.email_service import EmailService
from src.services.ml.classify_diabetes import ClassifyDiabetesService
from src.services.search.hybrid_search_service import HybridSearchService

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class AgentTools:
    def __init__(
        self,
        search_service: HybridSearchService,
        calendar_service: CalendarService,
        diabetes_classifier_service: ClassifyDiabetesService,
        email_service: EmailService,
    ):
        self.search_service = search_service
        self.calendar_service = calendar_service
        self.diabetes_classifier_service = diabetes_classifier_service
        self.email_service = email_service

    def search_clinic_database(self, query: str) -> str:
        """
        Search the clinic database using RAG system.
        Automatically triggers web search if relevance score is below 0.6.
        """
        result = self.search_service.search(query)
        return result

    def search_web(self, query: str) -> str:
        """
        Search the web using Tavily and format results with URLs as references.

        Args:
            query: The search query from the user

        Returns:
            Formatted response with content and URL references
        """
        result = self.search_service.web_service.search(query)
        return result

    def classify_diabetes(self, data: str):
        """
        Classify a patient's diabetes based on various factors.
        returns a string with the probability of the patient being diabetic and the final diagnosis.
        """
        result = self.diabetes_classifier_service.classify_diabetes(data)
        return result

    def list_available_slots(self, _="") -> str:
        """
        List all available appointments from google calendar.
        Use this to find the next available appointment times starting today
        and excluding weekends.
        """
        slots = self.calendar_service.list_available_slots()
        return slots

    def book_appointment(self, data: str) -> str:
        """
        Book an appointment on Google Calendar.

        Args:
            data: String containing appointment data in the following format:
            date_str='November 03, 2025', time_str='01:40 PM', patient_name='Ali', patient_age=25, description='Test', patient_email='test@example.com'

        Returns:
            Confirmation message containing the event ID and a link to the event in Google Calendar.
        """
        result = self.calendar_service.book_appointment(data)
        return result

    def cancel_appointment(self, event_id: str) -> str:
        result = self.calendar_service.cancel_appointment(event_id)
        return result
