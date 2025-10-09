# memorycare_app/utils/llm_client.py
import os, requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "INSERT API KEY"
                           )
OPENAI_BASE = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
# choose a model you have access to in your org/project
PREFERRED = os.getenv("OPENAI_MODEL", "").strip()
FALLBACKS = [m for m in [PREFERRED, "gpt-4.1-mini"] if m]

def chat(system_text: str, messages: list) -> str:
    if not OPENAI_API_KEY:
        return "[OpenAI key missing]"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    for model in FALLBACKS:
        body = {"model": model, "messages": [{"role": "system", "content": system_text}, *messages]}
        try:
            r = requests.post(f"{OPENAI_BASE}/chat/completions", headers=headers, json=body, timeout=60)
            if r.status_code == 200:
                data = r.json()
                return data["choices"][0]["message"]["content"]
            else:
                # try next model
                continue
        except Exception:
            continue

    return "[All configured models unavailable in this project. Please set OPENAI_MODEL to one you can use.]"