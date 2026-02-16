from src.settings.paths import DIABETES_MODEL_PATH
from src.services.ml.classify_diabetes import ClassifyDiabetesService


_diabetes_service_instance = None


def get_diabetes_service():
    global _diabetes_service_instance

    if _diabetes_service_instance is None:
        import joblib

        model = joblib.load(DIABETES_MODEL_PATH)
        _diabetes_service_instance = ClassifyDiabetesService(model=model)

    return _diabetes_service_instance
