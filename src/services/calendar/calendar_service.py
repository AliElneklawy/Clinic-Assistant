import datetime

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from models.appointment import BookAppointmentInput
from scripts import unpack_data
from services.calendar.event_builder import EventBuilder
from services.calendar.slot_manager import SlotManager
from services.database.database_service import DatabaseOpsService
from settings import clinic_config
from settings.logger import get_logger

logger = get_logger(__name__)


class CalendarService:
    def __init__(
        self,
        event_builder: EventBuilder,
        slot_manager: SlotManager,
        db: DatabaseOpsService,
        service: Resource,
    ):
        self.event_builder = event_builder
        self.slot_manager = slot_manager
        self.db = db
        self.service = service

    def list_available_slots(self) -> str:
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

            day_slots = self.slot_manager._generate_time_slots(current_date)
            available = []

            for slot_start, slot_end in day_slots:
                if self.slot_manager._is_slot_available(
                    slot_start, slot_end, existing_events
                ):
                    available.append(
                        f"{slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}"
                    )

            if available:
                slots[current_date.strftime("%A, %B %d, %Y")] = available

        return slots

    def book_appointment(self, data: str) -> str:
        """
        Book an appointment on Google Calendar.

        Args:
            data: String containing appointment data in the following format:
            date_str='November 03, 2025', time_str='01:40 PM', patient_name=None, patient_age=None, description=None, patient_email=None

        Returns:
            Confirmation message containing the event ID and a link to the event in Google Calendar.
        """
        (
            appointment_date,
            appointment_time,
            user_id,
            patient_name,
            patient_age,
            description,
            patient_email,
        ) = unpack_data.unpack(data, BookAppointmentInput)

        try:
            # Verify the slot is still available
            start_datetime = datetime.datetime.combine(
                appointment_date, appointment_time
            )
            end_datetime = start_datetime + datetime.timedelta(
                minutes=clinic_config.SLOT_DURATION_MINUTES
            )

            # Get existing events to check availability
            time_min = (
                datetime.datetime.combine(
                    appointment_date, datetime.time(0, 0)
                ).isoformat()
                + "Z"
            )
            time_max = (
                datetime.datetime.combine(
                    appointment_date, datetime.time(23, 59)
                ).isoformat()
                + "Z"
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

            # Check if slot is available
            if not self.slot_manager._is_slot_available(
                start_datetime, end_datetime, existing_events
            ):
                return f"The time slot at {appointment_time.strftime('%I:%M %p')} on {appointment_date.strftime('%B %d, %Y')} is no longer available. Please choose another time."

            # Create the event
            event = self.event_builder._create_event(
                patient_name,
                patient_age,
                patient_email,
                description,
                start_datetime,
                end_datetime,
            )

            created_event = (
                self.service.events()
                .insert(
                    calendarId=clinic_config.CALENDAR_ID,
                    body=event,
                    sendUpdates="all" if patient_email else "none",
                )
                .execute()
            )

            add_to_calendar_link = self.event_builder._make_add_to_calendar_link(
                title=f"Appointment: {patient_name}",
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                details=description,
                patient_email=patient_email,
            )

            self.db.insert_appointment(
                user_id,
                created_event["id"],
                patient_name,
                patient_age,
                patient_email,
                start_datetime,
                description,
                "scheduled",
            )
            logger.info("Successfuly added appointment details to the database.")

            result = (
                f"Appointment booked successfully for {patient_name or 'Patient'} on "
                f"{appointment_date.strftime('%B %d, %Y')} at {appointment_time.strftime('%I:%M %p')}. "
                f"Event ID: {created_event['id']}. Use this ID to cancel or reschedule the appointment. "
                f"Use this link to add the event to your calendar: {add_to_calendar_link}"
            )

            logger.info(f"Appointment booked: {result}")
            return result

        except HttpError as e:
            error_msg = f"Google Calendar API error: {str(e)}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error booking appointment: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def cancel_appointment(self, event_id: str) -> str:
        """
        Cancel an appointment from google calendar.
        """
        event_id = event_id.strip("O")
        try:
            self.service.events().delete(
                calendarId=clinic_config.CALENDAR_ID, eventId=event_id
            ).execute()
            # self.db.cancel_appointment(event_id)
            self.db.update_field(
                table_name="appointments",
                field_name="status",
                value="cancelled",
                condition=f"event_id = '{event_id}'",
            )
            return f"Appointment cancelled successfully for event ID: {event_id}"
        except HttpError as e:
            error_msg = f"Google Calendar API error: {str(e)}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error cancelling appointment: {str(e)}"
            logger.error(error_msg)
            return error_msg
