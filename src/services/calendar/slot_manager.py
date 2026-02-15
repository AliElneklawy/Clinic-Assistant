import datetime
from typing import List, Tuple

from src.settings import clinic_config


class SlotManager:
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
