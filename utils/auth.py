# memorycare_app/utils/auth.py
from typing import Optional
from datetime import datetime, timedelta
import secrets

_tokens = {}  # token -> {"role": "doctor"|"patient", "username": str, "expires": datetime}

def issue_doctor_token(username: str, password: str) -> Optional[str]:
    if username == "doctor" and password == "doctor":
        token = "doc_" + secrets.token_urlsafe(16)
        _tokens[token] = {"role": "doctor", "username": "doctor", "expires": datetime.utcnow() + timedelta(hours=8)}
        return token
    return None

def issue_patient_token(username: str) -> str:
    token = "pat_" + secrets.token_urlsafe(16)
    _tokens[token] = {"role": "patient", "username": username, "expires": datetime.utcnow() + timedelta(hours=8)}
    return token

def whoami(token: str) -> Optional[dict]:
    info = _tokens.get(token)
    if not info:
        return None
    if info["expires"] < datetime.utcnow():
        del _tokens[token]
        return None
    return info
