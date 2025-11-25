from scripts import create_folder
from services.database.db_schema import APPOINTMENTS_TABLE
from settings.paths import DATA_DIR
from utils.db_manager import db_connection


class DatabaseOpsService:
    def __init__(self, db_name: str) -> None:
        self.db_path = create_folder.create(DATA_DIR) / "database" / db_name
        self._init_db()

    def _init_db(self):
        with db_connection(self.db_path) as conn:
            conn.executescript(APPOINTMENTS_TABLE)

    def insert_appointment(
        self,
        user_id,
        event_id,
        patient_name,
        patient_age,
        patient_email,
        date_time,
        description,
        status,
    ):
        with db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO appointments (user_id, event_id, patient_name, patient_age, patient_email, date_time, description, status)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    event_id,
                    patient_name,
                    patient_age,
                    patient_email,
                    date_time,
                    description,
                    status,
                ),
            )

    def cancel_appointment(self, event_id: str):
        with db_connection(self.db_path) as conn:
            conn.execute(
                """
                UPDATE appointments
                SET status = 'cancelled'
                WHERE event_id = ?
                """,
                (event_id,)
            )
