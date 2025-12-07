from scripts import create_folder
from services.database.db_schema import APPOINTMENTS_TABLE, BOT_SUBS_TABLE
from settings.paths import DATA_DIR
from utils.db_manager import db_connection


class DatabaseOpsService:
    def __init__(self, db_name: str = "clinic.db") -> None:
        self.db_path = create_folder.create(DATA_DIR) / "database" / db_name
        self._init_db()

    def _init_db(self):
        with db_connection(self.db_path) as conn:
            conn.execute(APPOINTMENTS_TABLE)
            conn.execute(BOT_SUBS_TABLE)

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

    # def cancel_appointment(self, event_id: str):
    #     with db_connection(self.db_path) as conn:
    #         conn.execute(
    #             """
    #             UPDATE appointments
    #             SET status = 'cancelled'
    #             WHERE event_id = ?
    #             """,
    #             (event_id,),
    #         )

    def insert_bot_subscriber(self, user_id: str, chat_id: str):
        with db_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO bot_subscribers (user_id, chat_id)
                VALUES(?, ?)
                """,
                (user_id, chat_id),
            )

    def get_bot_subscribers(self, user_id: str | None = None, get_all: bool = False):
        if get_all:
            with db_connection(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM bot_subscribers")
                return cursor.fetchall()

        with db_connection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM bot_subscribers WHERE user_id = ?", (user_id,)
            )
            return cursor.fetchone()

    def get_medical_fact(self):
        with db_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT fact FROM medical_facts
                ORDER BY RANDOM()
                LIMIT 1
                """
            )

            return cursor.fetchone()[0]

    def get_appointments(self):
        with db_connection(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM appointments")
            return cursor.fetchall()

    def update_field(
        self, table_name: str, field_name: str, value: str, condition: str
    ):
        with db_connection(self.db_path) as conn:
            conn.execute(
                f"""
                UPDATE {table_name}
                SET {field_name} = ?
                WHERE {condition}
                """,
                (value,),
            )
