# memorycare_app/utils/models.py
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password: str
    full_name: str
    family_info: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    hobbies: Optional[str] = None  # NEW FIELD

    medications: List["Medication"] = Relationship(back_populates="patient")
    goals: List["Goal"] = Relationship(back_populates="patient")


class Medication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id", index=True)
    name: str
    times_per_day: int = 1
    specific_times: Optional[str] = None
    instructions: Optional[str] = None
    active: bool = True
    start_date: datetime = Field(default_factory=datetime.utcnow)  # NEW
    end_date: Optional[datetime] = None  # NEW - when to stop
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    patient: Patient = Relationship(back_populates="medications")
    logs: List["MedicationLog"] = Relationship(back_populates="medication")

class MedicationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    medication_id: int = Field(foreign_key="medication.id", index=True)
    date: datetime = Field(default_factory=datetime.utcnow)
    time_taken: Optional[str] = None
    taken: bool = False

    medication: Optional["Medication"] = Relationship(back_populates="logs")


    



class Goal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id", index=True)
    text: str
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    patient: Patient = Relationship(back_populates="goals")
