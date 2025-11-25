APPOINTMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    event_id TEXT,
    patient_name TEXT,
    patient_age REAL,
    patient_email TEXT,
    date_time INTEGER,      -- Unix timestamp for date
    description TEXT,
    status TEXT CHECK(status IN ('scheduled', 'cancelled')) DEFAULT 'scheduled'
);
"""
