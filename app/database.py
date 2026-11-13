import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/qadb")
logger.debug(f"Attempting to initialize database engine. URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0], '***')}") # Masking credentials in log

try:
    engine = create_engine(DATABASE_URL)
    logger.info("PostgreSQL engine successfully initialized.")
except Exception as e:
    logger.critical(f"Critical failure initializing PostgreSQL engine: {e}", exc_info=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        db.close()
        logger.debug("Database session closed.")