# ~/memmachine-project/memorycare_app/api/main.py
import os, uuid, random, json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlmodel import select

from utils.db import create_db_and_tables, get_session
from utils.models import Patient, Medication, Goal, MedicationLog
from utils.auth import issue_doctor_token, issue_patient_token, whoami
from utils.memmachine_client import MemMachine
from utils.llm_client import chat
from utils.scheduler import next_due_window

load_dotenv()

app = FastAPI(title="MemoryCare API")
create_db_and_tables()
mm = MemMachine()

DEMENTIA_SYSTEM_PROMPT = """You are MemoryCare Assistant, a warm and compassionate AI companion designed to help people with memory challenges.

## Your Personality
- Friendly, encouraging, and naturally conversational
- Think of yourself as a caring friend, not a database
- Offer helpful thoughts and suggestions even when you don't have stored memories
- Be genuinely interested in the person and their life

## How to Use Memories
- When you have relevant stored memories, weave them naturally into conversation
- Use phrases like: "You mentioned..." or "I remember you told me..."
- CRITICAL: Only reference facts that are explicitly in the Memory Context below
- Never confuse this user with information about other people

## When You Don't Have Memories
- Still be helpful and conversational!
- Offer general advice, ask engaging questions, or make thoughtful suggestions
- Example: If asked about hiking without stored preferences, say something like:
  "A hike sounds wonderful! Fresh air and nature can be so refreshing. Do you have any favorite trails, or would you like suggestions for your area?"
- Don't just say "I don't have that information" - be a real companion

## Important Rules
- NEVER mix up user identities - only use memories from THIS user
- If Memory Context mentions other people (like "Jason likes pie"), that's information ABOUT Jason stored BY this user, not about this user themselves
- The user you're talking to is: {user_name}
- Keep responses warm, brief (2-4 sentences), and clear
- Never say "you forgot" or make the user feel bad about memory gaps

## Memory Context for {user_name}
{memory_context}

Remember: Be their companion, not just their memory bank. Even without stored memories, you can still be helpful, warm, and engaging.
"""

# ============================
#        SCHEMAS
# ============================

class DoctorLogin(BaseModel):
    username: str
    password: str

class PatientSignup(BaseModel):
    username: str
    password: str
    full_name: str
    family_info: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    hobbies: Optional[str] = None

class PatientLogin(BaseModel):
    username: str
    password: str

class MedicationIn(BaseModel):
    patient_username: str
    name: str
    times_per_day: int = 1
    specific_times: Optional[str] = None
    instructions: Optional[str] = None
    active: bool = True

class GoalIn(BaseModel):
    text: str

class ChatRequest(BaseModel):
    user_id: str
    message: str
    token: Optional[str] = None
    message_count: Optional[int] = 0
    medication_taken: Optional[Dict[str, Any]] = {}

class RememberRequest(BaseModel):
    user_id: str
    text: str

# HELPER FUNCTION FOR MEDICATION RESET #
def check_and_reset_medications(patient_id: int):
    """Check medication expiration and reset daily counts"""
    with get_session() as s:
        today = datetime.now().date()
        
        # Get active medications
        meds = s.exec(select(Medication).where(
            Medication.patient_id == patient_id,
            Medication.active == True
        )).all()
        
        for med in meds:
            # Check if medication period is over
            if med.end_date and med.end_date.date() < today:
                med.active = False
                s.add(med)
        
        s.commit()

# FILTER FUNCTION FOR MEMORY EXTRACTION AND ROUTING #
def extract_and_route_memories(user_id: str, user_message: str, assistant_reply: str) -> List[Dict[str, Any]]:
    """
    Extracts facts and determines which user they should be stored under.
    Returns list of {user_id, text, tags} to store.
    """
    
    routing_prompt = f"""You are analyzing a conversation to extract and route factual information.

                CRITICAL CONTEXT: 
                - The person speaking is: {user_id}
                - Extract ONLY facts about {user_id} or information {user_id} is sharing
                - Store everything from {user_id}'s first-person perspective

                RULES:
                1. Extract facts in FIRST-PERSON from {user_id}'s perspective
                2. If {user_id} mentions someone else (like "Jason likes pie"), store it as: "Jason likes pie" (it's {user_id}'s memory about Jason)
                3. ALWAYS route to {user_id} - this is {user_id}'s conversation
                4. DO NOT STORE if:
                - It's just a question
                - It's a greeting or small talk
                - The assistant is offering suggestions (don't store assistant's ideas as facts)

                CURRENT USER SPEAKING: {user_id}

                User ({user_id}) said: "{user_message}"
                Assistant replied: "{assistant_reply}"

                Output format (one per line):
                STORE_FOR:{user_id}|[category]|First-person fact
                NO_STORAGE (if nothing to store)

                Categories: personal, family, medical, preference, routine, memory, location

                Examples where user is "molly":
                - If molly says "I like hiking":
                STORE_FOR:molly|[preference]|I like hiking

                - If molly says "Jason likes to eat pie":
                STORE_FOR:molly|[memory]|Jason likes to eat pie
                (This is molly's knowledge about Jason, stored under molly)

                - If molly asks "should I go on a hike?":
                NO_STORAGE
                (Just a question, no facts to store)

                - If molly says "I need to find a place to hike":
                STORE_FOR:molly|[preference]|I like hiking
                (Implies molly likes hiking)

                Your extraction:"""

    try:
        extraction = chat(
            "You are a memory routing specialist.",
            [{"role": "user", "content": routing_prompt}]
        )
        
        if "NO_STORAGE" in extraction.upper():
            return []
        
        memories_to_store = []
        for line in extraction.strip().split("\n"):
            line = line.strip()
            if not line or "NO_STORAGE" in line:
                continue
            
            # Parse STORE_FOR:user|[category]|fact
            if line.startswith("STORE_FOR:"):
                try:
                    parts = line.split("|", 2)
                    target_user = parts[0].replace("STORE_FOR:", "").strip()
                    category = parts[1].strip().replace("[", "").replace("]", "")
                    fact = parts[2].strip()
                    
                    if fact and len(fact.split()) >= 3:
                        memories_to_store.append({
                            "user_id": target_user,
                            "text": fact,
                            "category": category
                        })
                except Exception as e:
                    print(f"[WARN] Failed to parse line: {line} | {e}")
                    continue
        
        return memories_to_store
        
    except Exception as e:
        print(f"[ERROR] Memory routing failed: {e}")
        return []
    

def should_attempt_extraction(message: str) -> bool:
    """
    Quick heuristic to decide if message might contain storable information.
    Avoids expensive LLM calls for obvious questions and small talk.
    
    Returns True if message likely contains facts worth storing.
    Returns False for questions, greetings, or brief responses.
    """
    message_lower = message.lower().strip()
    
    # 1. Filter out very short messages (unlikely to contain meaningful info)
    word_count = len(message.split())
    if word_count < 3:
        return False
    
    # 2. Filter out questions - these are requests for information, not statements of fact
    question_words = [
        "what", "who", "when", "where", "why", "how",
        "which", "whose", "whom",
        "do you", "can you", "could you", "would you", "will you",
        "should you", "are you", "is there", "did you",
        "tell me", "show me", "help me", "explain"
    ]
    
    if any(message_lower.startswith(q) for q in question_words):
        return False
    
    if message.endswith("?"):
        return False
    
    # 3. Filter out greetings and social pleasantries
    greetings = [
        "hello", "hi ", "hi,", "hey", "hey there",
        "good morning", "good afternoon", "good evening", "good night",
        "thanks", "thank you", "thank", "thx",
        "ok", "okay", "sure", "yes", "no", "yeah", "yep", "nope",
        "bye", "goodbye", "see you", "talk later"
    ]
    
    if any(message_lower.startswith(g) for g in greetings):
        return False
    
    # 4. Filter out system/meta requests
    meta_requests = [
        "clear", "delete", "reset", "forget",
        "remember this", "save this", "store this"  # explicit commands handled differently
    ]
    
    if any(meta in message_lower for meta in meta_requests):
        return False
    
    # 5. POSITIVE SIGNALS - Strong indicators of factual information
    info_indicators = [
        # Identity and personal info
        "i am", "i'm", "my name is", "i was born", "i live in",
        
        # Preferences and opinions
        "i like", "i love", "i enjoy", "i prefer", "i hate", "i don't like",
        "my favorite", "i want", "i need",
        
        # Relationships and family
        "my ", "my wife", "my husband", "my son", "my daughter",
        "my brother", "my sister", "my friend", "my mother", "my father",
        
        # Activities and routines
        "i work", "i go to", "i take", "i eat", "i drink", "i play",
        "i watch", "i read", "i listen", "i exercise",
        "every day", "every morning", "every night", "usually",
        
        # Medical and health (important for dementia care)
        "i have", "i take medication", "my doctor", "i'm allergic",
        
        # Past experiences and memories
        "i used to", "i remember", "i grew up", "when i was",
        "i worked at", "i went to", "i met"
    ]
    
    if any(indicator in message_lower for indicator in info_indicators):
        return True
    
    # 6. Check for proper nouns (names, places) - often indicates factual content
    # Simple heuristic: words that start with capital letters (excluding first word)
    words = message.split()
    if len(words) > 1:
        capitalized_count = sum(1 for word in words[1:] if word and word[0].isupper())
        if capitalized_count >= 1:  # Has at least one proper noun
            return True
    
    # 7. Default behavior for medium-length declarative statements
    # If it's 5+ words and doesn't match filters above, might be worth checking
    if word_count >= 5 and not message.endswith("?"):
        return True
    
    # 8. Default: don't extract (be conservative to save API calls)
    return False

# ============================
#        ROUTES
# ============================

@app.get("/health")
def health() -> Dict[str, Any]:
    try:
        return {"ok": True, "memmachine": mm.health()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------- AUTH --------------------
@app.post("/auth/doctor/login")
def doctor_login(payload: DoctorLogin):
    token = issue_doctor_token(payload.username, payload.password)
    if not token:
        raise HTTPException(401, "Invalid doctor credentials")
    return {"ok": True, "token": token, "role": "doctor"}

@app.post("/auth/patient/signup")
def patient_signup(payload: PatientSignup):
    with get_session() as s:
        existing = s.exec(select(Patient).where(Patient.username == payload.username)).first()
        if existing:
            raise HTTPException(409, "Username already exists")
        p = Patient(
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
            family_info=payload.family_info,
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_phone=payload.emergency_contact_phone,
            hobbies=payload.hobbies,
        )
        s.add(p)
        s.commit()

    token = issue_patient_token(payload.username)

    episodic_text = (
        f"{payload.full_name} signed up for MemoryCare on {datetime.now().strftime('%Y-%m-%d')}."
    )
    profile_data = {
        "full_name": payload.full_name,
        "family_info": payload.family_info or "Not provided",
        "emergency_contact_name": payload.emergency_contact_name or "Not provided",
        "emergency_contact_phone": payload.emergency_contact_phone or "Not provided",
        "hobbies": payload.hobbies or "Not shared",
        "category": "personal_info"
    }
    if payload.emergency_contact_name:
        profile_data["emergency_contact_name"] = payload.emergency_contact_name
    if payload.emergency_contact_phone:
        profile_data["emergency_contact_phone"] = payload.emergency_contact_phone
        # Store a combined emergency contact entry in profile memory
        mm.remember_profile(
            user_id=payload.username,
            key="emergency_contact",
            value=f"{payload.emergency_contact_name or 'Unknown'} - Phone: {payload.emergency_contact_phone}",
            category="emergency_info"
        )
    mm.store_dual_memory(
        user_id=payload.username,
        episodic_text=episodic_text,
        profile_data=profile_data,
        tags=["signup", "profile_creation"]
    )
    return {"ok": True, "token": token, "role": "patient"}

@app.post("/auth/patient/login")
def patient_login(payload: PatientLogin):
    with get_session() as s:
        p = s.exec(select(Patient).where(Patient.username == payload.username)).first()
        if not p or p.password != payload.password:
            raise HTTPException(401, "Invalid credentials")
    mm.remember(
        user_id=payload.username,
        text=f"Patient logged in on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        tags=["login", "activity"]
    )
    token = issue_patient_token(payload.username)
    return {"ok": True, "token": token, "role": "patient"}

# -------------------- DOCTOR ROUTES --------------------
@app.get("/doctor/patients")
def list_patients(token: str = Query(...)):
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")
    with get_session() as s:
        patients = s.exec(select(Patient)).all()
        return {"ok": True, "patients": [{"username": p.username, "full_name": p.full_name, "id": p.id} for p in patients]}

@app.post("/doctor/medications")
def add_med(payload: MedicationIn, token: str = Query(...), duration_days: int = Query(7)):
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")
    start = datetime.now()
    end = start + timedelta(days=duration_days)
    
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == payload.patient_username)).first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        existing = s.exec(select(Medication).where(
            Medication.patient_id == patient.id,
            Medication.name == payload.name,
            Medication.active == True
        )).first()

        if existing:
            raise HTTPException(400, f"Active medication '{payload.name}' already exists")
        
        med = Medication(
            patient_id=patient.id,
            name=payload.name,
            times_per_day=payload.times_per_day,
            specific_times=payload.specific_times,
            instructions=payload.instructions,
            active=payload.active,
        )
        s.add(med)
        s.commit()
    episodic_text = f"Doctor added new medication '{payload.name}' on {datetime.now().strftime('%Y-%m-%d')}."
    profile_data = {
        f"medication_{payload.name.lower().replace(' ', '_')}": f"{payload.name} - {payload.times_per_day}x daily at {payload.specific_times}",
        "category": "medical_info"
    }
    mm.store_dual_memory(
        user_id=payload.patient_username,
        episodic_text=episodic_text,
        profile_data=profile_data,
        tags=["medication", "doctor_action"]
    )
    return {"ok": True, "message": "Medication added"}

@app.get("/doctor/patient-goals")
def get_patient_goals(patient_username: str = Query(...), token: str = Query(...)):
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == patient_username)).first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        all_goals = s.exec(select(Goal).where(Goal.patient_id == patient.id)).all()
        return {"ok": True, "goals": [
            {**g.model_dump(), "completed_at_str": g.completed_at.strftime("%Y-%m-%d %H:%M") if g.completed_at else None}
            for g in all_goals
        ]}

@app.get("/doctor/patient-medications")
def doctor_view_meds(patient_username: str = Query(...), token: str = Query(...)):
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == patient_username)).first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        meds = s.exec(select(Medication).where(Medication.patient_id == patient.id)).all()
        data = []
        for m in meds:
            logs = s.exec(select(MedicationLog).where(MedicationLog.medication_id == m.id)).all()
            data.append({
                "name": m.name,
                "times_per_day": m.times_per_day,
                "specific_times": m.specific_times,
                "instructions": m.instructions,
                "logs": [{"date": l.date.strftime("%Y-%m-%d"), "time_taken": l.time_taken, "taken": l.taken} for l in logs]
            })
        return {"ok": True, "medications": data}
    
@app.post("/doctor/goals")
def add_goal(payload: GoalIn, patient_username: str = Query(...), token: str = Query(...)):
    info = whoami(token)
    if not info or info["role"] != "doctor":
        raise HTTPException(401, "Doctor auth required")

    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == patient_username)).first()
        if not patient:
            raise HTTPException(404, "Patient not found")
        goal = Goal(patient_id=patient.id, text=payload.text)
        s.add(goal)
        s.commit()
    
    # EPISODIC MEMORY: Record goal assignment
    episodic_text = f"Doctor assigned new goal on {datetime.now().strftime('%Y-%m-%d')}: {payload.text}"
    
    # PROFILE MEMORY: Store as active goal
    profile_data = {
        f"active_goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}": payload.text,
        "category": "goals"
    }
    
    mm.store_dual_memory(
        user_id=patient_username,
        episodic_text=episodic_text,
        profile_data=profile_data,
        tags=["goal", "doctor_action"]
    )
    
    return {"ok": True, "message": "Goal assigned"}


# -------------------- PATIENT ROUTES --------------------
@app.get("/patient/goals")
def list_goals(token: str = Query(...)):
    me = whoami(token)
    if not me or me["role"] != "patient":
        raise HTTPException(401, "Patient auth required")
    with get_session() as s:
        p = s.exec(select(Patient).where(Patient.username == me["username"])).first()
        goals = s.exec(select(Goal).where(Goal.patient_id == p.id, Goal.completed == False)).all()
        return {"ok": True, "goals": [g.model_dump() for g in goals]}

@app.get("/patient/medications")
def list_medications(token: str = Query(...)):
    me = whoami(token)
    if not me or me["role"] != "patient":
        raise HTTPException(401, "Patient auth required")
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == me["username"])).first()
        check_and_reset_medications(patient.id)
        meds = s.exec(select(Medication).where(Medication.patient_id == patient.id, Medication.active == True)).all()
        result = []
        for m in meds:
            logs = s.exec(select(MedicationLog).where(MedicationLog.medication_id == m.id)).all()
            result.append({
                "name": m.name,
                "times_per_day": m.times_per_day,
                "specific_times": m.specific_times,
                "instructions": m.instructions,
                "logs": [{"date": l.date.strftime("%Y-%m-%d"), "time_taken": l.time_taken, "taken": l.taken} for l in logs]
            })
        return {"ok": True, "medications": result}

@app.post("/patient/medications/log")
def log_medication(med_name: str = Query(...), token: str = Query(...)):
    me = whoami(token)
    if not me or me["role"] != "patient":
        raise HTTPException(401, "Patient auth required")
    
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == me["username"])).first()
        med = s.exec(select(Medication).where(
            Medication.patient_id == patient.id, 
            Medication.name == med_name,
            Medication.active == True
        )).first()
        
        if not med:
            raise HTTPException(404, "Medication not found")
        
        # Check today's logs
        today = datetime.now().date()
        today_logs = s.exec(select(MedicationLog).where(
            MedicationLog.medication_id == med.id,
            MedicationLog.date >= datetime.combine(today, datetime.min.time())
        )).all()
        
        # Prevent over-logging
        if len(today_logs) >= med.times_per_day:
            raise HTTPException(400, f"Already logged {med.times_per_day} doses today")
        
        log_entry = MedicationLog(
            medication_id=med.id, 
            taken=True, 
            time_taken=datetime.now().strftime("%H:%M")
        )
        s.add(log_entry)
        s.commit()
    
    mm.remember(
        user_id=me["username"],
        text=f"Took {med_name} at {datetime.now().strftime('%H:%M')} on {datetime.now().strftime('%Y-%m-%d')}",
        tags=["medication_log"]
    )
    return {"ok": True, "message": f"Logged {med_name} as taken."}

# -------------------- MEMORY & CHAT --------------------
@app.post("/remember")
def remember(req: RememberRequest) -> Dict[str, Any]:
    try:
        saved = mm.remember(user_id=req.user_id, text=req.text)
        return {"ok": True, "saved": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Existing chat_with_memory function remains unchanged



# -------------------- chat with persistent memory --------------------
@app.post("/chat")
def chat_with_memory(req: ChatRequest):
    user_id = req.user_id
    
    # Check if this is system-initiated conversation
    is_system_start = req.message == "__SYSTEM_START__"
    
    # Get message count and medication tracking from request
    message_count = req.dict().get("message_count", 0)
    medication_taken = req.dict().get("medication_taken", {})

    # Retrieve EPISODIC memories
    episodic_memories = mm.retrieve(user_id=user_id, query=req.message if not is_system_start else "all memories", top_k=12)
    if not episodic_memories:
        episodic_memories = mm.retrieve(user_id=user_id, query="all memories", top_k=20)
    
    # Retrieve PROFILE memories
    profile_memories = mm.retrieve_profile(user_id=user_id)
    
    print(f"[DEBUG] Episodic memories count: {len(episodic_memories)}")
    print(f"[DEBUG] Profile memories count: {len(profile_memories)}")

    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.username == user_id)).first()
        if patient:
            check_and_reset_medications(patient.id)

        meds = s.exec(select(Medication).where(Medication.patient_id == patient.id, Medication.active == True)).all() if patient else []
        goals = s.exec(select(Goal).where(Goal.patient_id == patient.id, Goal.completed == False)).all() if patient else []

    med_status_lines = []
    for m in meds:
        today_str = datetime.now().strftime("%Y-%m-%d")
        logs = s.exec(select(MedicationLog).where(
            MedicationLog.medication_id == m.id,
            MedicationLog.date >= datetime.combine(datetime.now().date(), datetime.min.time())
        )).all()
        
        taken_count = len(logs)
        remaining = m.times_per_day - taken_count
        
        if remaining > 0:
            med_status_lines.append(f"⚠️ {m.name}: {taken_count}/{m.times_per_day} taken, {remaining} remaining today")
        else:
            med_status_lines.append(f"✅ {m.name}: All doses complete ({m.times_per_day}/{m.times_per_day})")

    medication_status = "\n".join(med_status_lines) if med_status_lines else "No active medications"


    # Process EPISODIC memories
    episodic_lines = []
    for r in episodic_memories:
        if isinstance(r, dict):
            content = r.get("content") or r.get("episode_content") or r.get("text", "")
            if content:
                episodic_lines.append(content)
        elif isinstance(r, str):
            episodic_lines.append(r)
    episodic_snippets = "\n".join(f"- {m}" for m in episodic_lines if m).strip() or "No recent memories."
    
    # Process PROFILE memories
    profile_lines = []
    for p in profile_memories:
        if isinstance(p, dict):
            content = p.get("episode_content", "") or p.get("content", "") or p.get("text", "")
            if content:
                profile_lines.append(content)
    
    # Add database profile info as backup
    if patient:
        if patient.family_info:
            profile_lines.append(f"Family: {patient.family_info}")
        if patient.hobbies:
            profile_lines.append(f"Hobbies: {patient.hobbies}")
        if patient.emergency_contact_name:
            emergency_info = (f"Emergency Contact: {patient.emergency_contact_name}")
            if patient.emergency_contact_phone:
                emergency_info += f" - Phone: {patient.emergency_contact_phone}"
            profile_lines.append(emergency_info)
    
    profile_snippets = "\n".join(f"- {p}" for p in profile_lines if p).strip() or "No profile information."
    
    print(f"[DEBUG] Profile snippets:\n{profile_snippets}")

    hobbies = patient.hobbies if patient and patient.hobbies else "No hobbies listed"
    goals_line = ", ".join([g.text for g in goals]) if goals else "None right now."

    # Prepare medication info
    now = datetime.now()
    due_lines = []
    for m in meds:
        msg = next_due_window(now, m.times_per_day, m.specific_times)
        if msg:
            due_lines.append(f"{m.name}: {msg} {m.instructions or ''}")

    emergency_contact = ""
    if patient:
        if patient.emergency_contact_name and patient.emergency_contact_phone:
            emergency_contact = f"Emergency Contact: {patient.emergency_contact_name} - Phone: {patient.emergency_contact_phone}"
        elif patient.emergency_contact_name:
            emergency_contact = f"Emergency Contact: {patient.emergency_contact_name}" 

    # Create system prompt based on context
    if is_system_start:
        system = (
            "You are MemoryCare, a compassionate AI companion. This is the FIRST message - greet the user warmly! "
            "Welcome them by name, ask how they're feeling today, and mention you're here to support them. "
            "Be friendly, warm, and conversational. Start the conversation naturally."
        )
        user_payload = (
            f"Start a warm, welcoming conversation with {patient.full_name if patient else user_id}. "
            f"Their hobbies include: {hobbies}. "
            f"Greet them warmly and ask how they're doing today."
        )
    else:
        system = (
            "You are MemoryCare, a compassionate companion for dementia or Alzheimer's patients. "
            "Talk like a warm, caring friend. Use the profile information provided to give personalized responses. "
            "When asked about family, hobbies, or personal details, USE THE PROFILE INFORMATION to answer. "
            "Ask about their day, feelings, family, hobbies, and routines naturally. "
            "Encourage them kindly, and celebrate when they share progress."
        )
        

        user_payload = (
            f"User said: {req.message}\n\n"
            f"=== MEDICATION STATUS TODAY ===\n{medication_status}\n\n"
            f"=== PROFILE INFORMATION (Use this to answer questions) ===\n{profile_snippets}\n\n"
            f"=== RECENT MEMORIES ===\n{episodic_snippets}\n\n"
            f"Additional Info:\n"
            f"- Full Name: {patient.full_name if patient else 'Unknown'}\n"
            f"- Hobbies: {hobbies}\n"
            f"- Goals: {goals_line}\n"
            f"- Medications: {', '.join([m.name for m in meds]) if meds else 'None'}\n"
            f"- {emergency_contact if emergency_contact else 'Emergency Contact: Not provided'}\n"
        )

    reply = chat(system, [{"role": "user", "content": user_payload}])

    # ------------------------------------------
    # 💾 1. Run factual memory extraction + routing
    # ------------------------------------------
    try:
        if should_attempt_extraction(req.message):
            routed_memories = extract_and_route_memories(
                user_id=user_id,
                user_message=req.message,
                assistant_reply=reply
            )

            for mem in routed_memories:
                mm.remember(
                    user_id=mem["user_id"],
                    text=mem["text"],
                    tags=[mem["category"]]
                )
            print(f"[DEBUG] Stored {len(routed_memories)} extracted memories.")
        else:
            print("[DEBUG] Skipped extraction (message not factual enough).")
    except Exception as e:
        print(f"[ERROR] Memory extraction failed: {e}")
    # Goal completion detection (same as before)

    if goals and not is_system_start:
        completion_check_prompt = (
            "You are helping to track progress for a dementia patient. "
            "Given the user's latest message below and their active goals, "
            "determine if they clearly achieved or completed any of the goals. "
            "Respond strictly in JSON list format of completed goal texts.\n\n"
            f"Active goals: {[g.text for g in goals]}\n"
            f"User message: {req.message}"
        )
        try:
            result = chat(
                "You are a JSON parser that outputs only JSON list of completed goals.",
                [{"role": "user", "content": completion_check_prompt}],
            )
            completed = []
            try:
                completed = json.loads(result)
            except Exception:
                pass

            if completed:
                with get_session() as s:
                    patient = s.exec(select(Patient).where(Patient.username == user_id)).first()
                    active = s.exec(select(Goal).where(Goal.patient_id == patient.id, Goal.completed == False)).all()
                    for g in active:
                        if any(g.text.lower() == c.lower() for c in completed):
                            g.completed = True
                            g.completed_at = datetime.utcnow()
                            s.add(g)
                    s.commit()

                    remaining = s.exec(select(Goal).where(Goal.patient_id == patient.id, Goal.completed == False)).all()
                    remaining_text = ", ".join([g.text for g in remaining]) or "No active goals now 🎉"

                    mm.remember(user_id=user_id, text=f"Goal completed on {datetime.now().strftime('%Y-%m-%d')}: {', '.join(completed)}", tags=["goal_completion", "achievement"])
                    
                    reply += (
                        f"\n🎉 That's wonderful! Congratulations on completing: {', '.join(completed)}. "
                        f"You're doing great! Active goals now: {remaining_text}"
                    )
        except Exception as e:
            print("Goal check failed:", e)

    # Extract profile information (only for user messages, not system start)
    if not is_system_start:
        profile_extraction_prompt = (
            "Extract any NEW permanent facts about the user from this conversation. "
            "Look for: preferences, likes/dislikes, relationships, routines, medical info. "
            "Return ONLY a JSON object with keys as fact names and values as facts. "
            "If no new profile facts, return empty object {}.\n\n"
            f"User: {req.message}\nAssistant: {reply}"
        )
        try:
            profile_result = chat("You extract profile facts and return only JSON.", [{"role": "user", "content": profile_extraction_prompt}])
            new_profile_facts = {}
            try:
                new_profile_facts = json.loads(profile_result)
            except Exception:
                pass
            
            if new_profile_facts:
                for key, value in new_profile_facts.items():
                    if value and isinstance(value, str):
                        mm.remember_profile(
                            user_id=user_id,
                            key=key,
                            value=value,
                            category="learned_preferences"
                        )
        except Exception as e:
            print("Profile extraction failed:", e)
        # Emotional check-in
        if any(word in req.message.lower() for word in ["feeling", "today", "tired", "happy", "sad", "enjoyed", "worried", "anxious"]):
            mm.remember(
                user_id=user_id,
                text=f"Emotional check-in on {datetime.now().strftime('%Y-%m-%d')}: {req.message}",
                tags=["emotional", "wellbeing"]
            )

    return {
        "ok": True,
        "reply": reply,
        "episodic_memories_used": len(episodic_lines),
        "profile_facts_available": len(profile_lines),
        "goals": [g.text for g in goals],
    }