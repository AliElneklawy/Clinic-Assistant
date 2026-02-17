from googleapiclient.discovery import build

from src.scripts.auth_calendar import authenticate_calendar
from src.services.calendar.calendar_service import CalendarService
from src.services.calendar.event_builder import EventBuilder
from src.services.calendar.slot_manager import SlotManager
from src.services.database.database_service import DatabaseOpsService

_calendar_service_instance = None


def get_calendar_service():
    global _calendar_service_instance

    if _calendar_service_instance is None:
        db_service = DatabaseOpsService()
        event_builder = EventBuilder()
        slot_manager = SlotManager()

        _calendar_service_instance = CalendarService(
            event_builder=event_builder,
            slot_manager=slot_manager,
            db=db_service,
            service=build("calendar", "v3", credentials=authenticate_calendar()),
        )

    return _calendar_service_instance
