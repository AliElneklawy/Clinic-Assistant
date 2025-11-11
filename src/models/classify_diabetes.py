from typing import Literal

from pydantic import BaseModel


class ClassifyDiabetesInput(BaseModel):
    gender: Literal["Male", "Female"]
    age: int
    hypertension: Literal["yes", "no"]
    heart_disease: Literal["yes", "no"]
    smoking_history: Literal[
        "never", "no_info", "former", "current", "not_current", "ever"
    ]
    bmi: float
    HbA1c_level: float
    blood_glucose_level: float
