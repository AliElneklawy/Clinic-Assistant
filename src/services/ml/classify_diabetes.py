import numpy as np
import pandas as pd

from src.models.classify_diabetes import ClassifyDiabetesInput
from src.scripts import unpack_data


class ClassifyDiabetesService:
    def __init__(self, model) -> None:
        self.model = model

    def preprocess(
        self,
        gender,
        age,
        hypertension,
        heart_disease,
        smoking_history,
        bmi,
        HbA1c_level,
        blood_glucose_level,
    ):
        df = pd.DataFrame(
            {
                "gender": [gender],
                "age": [age],
                "hypertension": [hypertension],
                "heart_disease": [heart_disease],
                "smoking_history": [smoking_history],
                "bmi": [bmi],
                "HbA1c_level": [HbA1c_level],
                "blood_glucose_level": [blood_glucose_level],
            }
        )

        df["AgeCat"] = pd.cut(
            df["age"],
            bins=[-np.inf, 1, 12, 18, 65, np.inf],
            labels=["infant", "child", "teenager", "adult", "older_adult"],
        )

        df["BMICat"] = pd.cut(
            df["bmi"],
            bins=[-np.inf, 18.5, 25, 30, np.inf],
            labels=["underweight", "normal", "overweight", "obese"],
        )

        df["GlucoseCat"] = pd.cut(
            df["blood_glucose_level"],
            bins=[-np.inf, 140, 200, np.inf],
            labels=["normal", "impaired", "diabetic"],
        )

        df["HbA1cCat"] = pd.cut(
            df["HbA1c_level"],
            bins=[0, 5.6, 6.4, np.inf],
            labels=["normal", "prediabetic", "diabetic"],
        )

        return df

    def classify_diabetes(self, data: str | ClassifyDiabetesInput):
        """
        Classify a patient's diabetes based on various factors.
        returns a string with the probability of the patient being diabetic and the final diagnosis.
        """
        # (
        #     gender,
        #     age,
        #     hypertension,
        #     heart_disease,
        #     smoking_history,
        #     bmi,
        #     HbA1c_level,
        #     blood_glucose_level,
        # ) = unpack_data.unpack(data, ClassifyDiabetesInput)

        if isinstance(data, str):
            data = unpack_data.unpack(data, ClassifyDiabetesInput)

        df = self.preprocess(
            data.gender,
            data.age,
            data.hypertension,
            data.heart_disease,
            data.smoking_history,
            data.bmi,
            data.HbA1c_level,
            data.blood_glucose_level,
        )

        prediction = self.model.predict(df)
        prediction_proba = self.model.predict_proba(df)[0][1]

        return f"Probability of being diabetic: {(prediction_proba * 100).round(2)}%.\nDiagnosis: {'diabetic' if prediction == 1 else 'non-diabetic'}."
