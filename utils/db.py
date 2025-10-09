# memorycare_app/utils/db.py
from sqlmodel import SQLModel, create_engine, Session

DB_URL = "sqlite:///app.db"
engine = create_engine(DB_URL, echo=False)

def get_session() -> Session:
    return Session(engine)

def create_db_and_tables():
    from .models import Patient, Medication, Goal, MedicationLog
    SQLModel.metadata.create_all(engine)