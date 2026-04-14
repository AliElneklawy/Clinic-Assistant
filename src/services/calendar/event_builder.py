import datetime
from urllib.parse import quote_plus, urlencode

from src.settings import clinic_config


class EventBuilder:
    def _make_add_to_calendar_link(
        self,
        title: str,
        start_datetime: datetime.datetime,
        end_datetime: datetime.datetime,
        details: str,
        patient_email: str = "",
    ) -> str:
        params = {
            "action": "TEMPLATE",
            "text": title,
            "dates": f"{start_datetime.strftime('%Y%m%dT%H%M00')}/{end_datetime.strftime('%Y%m%dT%H%M00')}",
            "details": details,
        }
        if patient_email:
            params["add"] = patient_email

        return "https://calendar.google.com/calendar/render?" + urlencode(
            params, quote_via=quote_plus
        )

    def _create_event(
        self,
        patient_name: str,
        patient_age: str,
        patient_email: str,
        description: str,
        start_datetime: datetime.datetime,
        end_datetime: datetime.datetime,
    ):
        event = {
            "summary": f"Appointment: {patient_name}, {patient_age} years old",
            "description": description,
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": clinic_config.CLINIC_TIMEZONE,
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": clinic_config.CLINIC_TIMEZONE,
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},  # 1 day before
                    {"method": "popup", "minutes": 60},  # 1 hour before
                ],
            },
        }

        if patient_email:
            event["attendees"] = [
                {"email": patient_email, "responseStatus": "needsAction"}
            ]

        return event
