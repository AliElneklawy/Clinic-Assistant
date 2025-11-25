from contextlib import contextmanager
import sqlite3


@contextmanager
def db_connection(path):
    conn = sqlite3.connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
