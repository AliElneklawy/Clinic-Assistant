import json
import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from services.database.database_service import DatabaseOpsService
from services.database.db_schema import MEDICAL_FACTS_TABLE
from utils.db_manager import db_connection


def insert_facts(db: DatabaseOpsService):
    with open("data/medical_facts.json", "r") as f:
        data = json.load(f)

    with db_connection(db.db_path) as conn:
        conn.execute(MEDICAL_FACTS_TABLE)
        for fact in data["medical_facts"]:
            conn.execute(
                """
                INSERT OR IGNORE INTO medical_facts (fact)
                VALUES(?)
                """,
                (fact,),
            )


if __name__ == "__main__":
    insert_facts(DatabaseOpsService())
