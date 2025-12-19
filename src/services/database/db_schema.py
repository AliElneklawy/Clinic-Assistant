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
    status TEXT CHECK(status IN ('scheduled', 'cancelled', 'confirmed')) DEFAULT 'scheduled',
    confirmation_sent BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE
);
"""

BOT_SUBS_TABLE = """
CREATE TABLE IF NOT EXISTS bot_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    chat_id TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_fact TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

MEDICAL_FACTS_TABLE = """
CREATE TABLE IF NOT EXISTS medical_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact TEXT UNIQUE
);
"""
