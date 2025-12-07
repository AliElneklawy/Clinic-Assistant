from pathlib import Path

BASE_DIR = Path(__file__).parents[2]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
INDEXES_DIR = DATA_DIR / "indexes"
MED_DATA_FILE = DATA_DIR / "content" / "medical_data.txt"
DISEASE_CONDITION_FILE = DATA_DIR / "content" / "diseases_conditions.txt"
DATASET_FILE = DATA_DIR / "content" / "diabetes.csv"
DIABETES_MODEL_PATH = DATA_DIR / "models" / "model.pkl"
