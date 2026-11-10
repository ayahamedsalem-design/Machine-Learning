from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# postgresql://username:password@host:port/database_name
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:mysecretpassword@localhost:5432/postgres"

# create engine 
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# create session to handle the base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# The fundamental rule for defining tables (models)
Base = declarative_base()

# A function to obtain a session and use it in APIs
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()