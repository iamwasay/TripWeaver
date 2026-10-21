import sqlite3
import json
from datetime import datetime
from app.utils.logger import logger

DB_PATH = "tripweaver.db"


def init_db():
    """Creates the SQLite table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id TEXT PRIMARY KEY,
            destination TEXT,
            budget REAL,
            status TEXT,
            created_at TEXT,
            payload TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized.")


def save_trip(
    trip_id: str, destination: str, budget: float, status: str, payload: dict
):
    """Saves the trip details to the local SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trips (id, destination, budget, status, created_at, payload) VALUES (?, ?, ?, ?, ?, ?)",
        (
            trip_id,
            destination,
            budget,
            status,
            datetime.utcnow().isoformat(),
            json.dumps(payload),
        ),
    )
    conn.commit()
    conn.close()
    logger.info(f"Trip {trip_id} saved to database.")


# Initialize the database when the module is imported
init_db()
