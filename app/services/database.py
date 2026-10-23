import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError, IntegrityError
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()

# Get DATABASE_URL from settings (default: sqlite:///./tripweaver.db)
# Render's Postgres gives 'postgres://' but SQLAlchemy needs 'postgresql://'
DATABASE_URL = settings.database_url
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine (pool_pre_ping ensures dead connections are recycled)
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class TripRecord(Base):
    __tablename__ = "trips"
    id = Column(String, primary_key=True)
    destination = Column(String, nullable=False)
    budget = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    payload = Column(Text, nullable=False)


def init_db():
    """Create the trips table if it doesn't exist."""
    try:
        Base.metadata.create_all(engine)
        provider = DATABASE_URL.split("://")[0]
        logger.info(f"Database initialized successfully ({provider}).")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


def save_trip(
    trip_id: str, destination: str, budget: float, status: str, payload: dict
) -> bool:
    """
    Save a trip to the audit database.
    Returns True if saved, False if the DB is unavailable (does NOT raise).
    This ensures a DB failure never blocks the user's trip response.
    """
    session = SessionLocal()
    try:
        existing = session.query(TripRecord).filter_by(id=trip_id).first()
        if existing:
            # Handle duplicate trip ID - update instead of crashing
            logger.info(f"Trip {trip_id} already exists, updating.")
            existing.destination = destination
            existing.budget = budget
            existing.status = status
            existing.payload = json.dumps(payload)
        else:
            record = TripRecord(
                id=trip_id,
                destination=destination,
                budget=budget,
                status=status,
                payload=json.dumps(payload),
            )
            session.add(record)

        session.commit()
        logger.info(f"Trip {trip_id} saved to audit log.")
        return True

    except OperationalError as e:
        # Database unavailable (read-only filesystem, network issue, etc.)
        logger.warning(f"Database write failed (trip will still be returned): {e}")
        session.rollback()
        return False

    except IntegrityError as e:
        logger.warning(f"Duplicate trip ID: {e}")
        session.rollback()
        return False

    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        session.rollback()
        return False

    finally:
        session.close()


def count_trips() -> int:
    """Return the total number of trips stored (used by /db-status)."""
    session = SessionLocal()
    try:
        return session.query(TripRecord).count()
    except Exception:
        return -1
    finally:
        session.close()


# Initialize on import
init_db()
