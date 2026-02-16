from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator


class BookAppointmentInput(BaseModel):
    date_str: date = Field(..., description="Appointment date")
    time_str: time = Field(
        ..., 
        description="Appointment time", 
        json_schema_extra={"examples": ["01:40 PM", "14:30", "9:00"]}
    )
    user_id: str = Field(..., description="User ID")
    patient_name: str = Field(..., description="Name of the patient")
    patient_age: int = Field(..., description="Age of the patient")
    description: str = Field(..., description="Reason for visit")
    patient_email: str = Field(..., description="Patient email")

    # Normalize date formats like "November 03, 2025" → date(2025, 11, 3)
    @field_validator("date_str", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            for fmt in ("%B %d, %Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(v.strip(), fmt).date()
                except ValueError:
                    continue
        raise ValueError(f"Invalid date format: {v}")

    # Normalize time formats like "01:40 PM" → time(13, 40)
    @field_validator("time_str", mode="before")
    @classmethod
    def parse_time(cls, v):
        if isinstance(v, time):
            return v
        if isinstance(v, str):
            for fmt in ("%I:%M %p", "%H:%M"):
                try:
                    return datetime.strptime(v.strip(), fmt).time()
                except ValueError:
                    continue
        raise ValueError(f"Invalid time format: {v}")

    @field_validator("patient_age", mode="before")
    @classmethod
    def parse_age(cls, v):
        if v in (None, ""):
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid age value: {v}")


# def parse_to_model(arg_str: str) -> BookAppointmentInput:
#     """
#     Parse the output of the LLM into a BookAppointmentInput model
#     to be properly handled by the book_appointment tool.
#     """
#     # Turn "a=1, b='x'" → "{'a':1, 'b':'x'}"
#     cleaned = re.sub(r"(\w+)\s*=", r"'\1':", arg_str)
#     cleaned = "{" + cleaned + "}"
#     data = ast.literal_eval(cleaned)
#     return BookAppointmentInput(**data)


# raw = "date_str='November 03, 2025', time_str='01:40 PM', patient_name=None, patient_age=None, description=None, patient_email=None"
# appointment = parse_to_model(raw)
# # print(appointment, type(appointment))
# print(appointment.model_dump())
# # print(appointment.date_str)
