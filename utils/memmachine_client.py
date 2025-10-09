import os
import uuid
from typing import List, Dict, Any, Optional
import requests

BASE_URL = os.getenv("MEMMACHINE_BASE_URL", "http://localhost:8080")

class MemMachine:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or BASE_URL

    def health(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/health", timeout=10)
        r.raise_for_status()
        return r.json()

    def remember(self, user_id: str, text: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Stores a new memory in MemMachine using the v1/memories endpoint format.
        """
        payload = {
            "session": {
                "group_id": user_id,
                "agent_id": ["memorycare_app"],
                "user_id": [user_id],
                "session_id": str(uuid.uuid4())
            },
            "producer": "memorycare_app",
            "produced_for": user_id,
            "episode_content": text,
            "episode_type": "memory_entry",
            "metadata": {
                "tags": tags or [],
                "actual_user_id": user_id
            }
        }

        r = requests.post(f"{self.base_url}/v1/memories", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()

    def remember_profile(self, user_id: str, key: str, value: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Store profile memory - permanent facts about the user."""
        payload = {
            "session": {
                "group_id": "memorycare_group",
                "agent_id": ["memorycare_app"],
                "user_id": [user_id],
                "session_id": str(uuid.uuid4())
            },
            "producer": "memorycare_app",
            "produced_for": user_id,
            "episode_content": f"{key}: {value}",  # Store as episode content
            "episode_type": category or "profile_info",
            "metadata": {
                "type": "profile",
                "key": key,
                "value": value,
                "category": category or "personal",
                "actual_user_id": user_id

            }
        }
        try:
            # Use /v1/memories/profile endpoint
            r = requests.post(f"{self.base_url}/v1/memories/profile", json=payload, timeout=20)
            if r.status_code not in (200, 201):
                print("[WARN] profile write failed:", r.text)
            return {"ok": r.status_code in (200, 201)}
        except Exception as e:
            print("[ERROR] profile write exception:", e)
            return {"ok": False, "error": str(e)}

    def retrieve(self, user_id: str, query: Optional[str] = None, top_k: int = 10) -> list:
        """
        Retrieve episodic memories for a user.
        Handles the nested response format:
        {"status":0, "content":{"episodic_memory":[[], [ {...}, {...} ], [""]]}}
        """
        import uuid

        if not query:
            query = "all memories"

        payload = {
            "session": {
                "group_id": user_id,
                "agent_id": ["memorycare_app"],
                "user_id": [user_id],
                "session_id": str(uuid.uuid4()),
            },
            "query": query,
            "limit": top_k * 3,
        }

        url = f"{self.base_url}/v1/memories/search"
        print(f"[INFO] Retrieving memories for {user_id} ...")

        try:
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()

            results = []

            # --- Correct unwrapping for your MemMachine response ---
            if (
                isinstance(data, dict)
                and "content" in data
                and "episodic_memory" in data["content"]
            ):
                episodic = data["content"]["episodic_memory"]
                # episodic is [[], [ {...}, {...} ], [""]]
                if isinstance(episodic, list) and len(episodic) > 1:
                    middle = episodic[1]
                    if isinstance(middle, list):
                        results = middle

            # fallback: if it's already a list of dicts
            elif isinstance(data, list):
                results = data
            elif isinstance(data, dict) and "results" in data:
                results = data["results"]
            else:
                print("[WARN] Unrecognized episodic response shape:", data)
                return []
            filtered = []
            for mem in results:
                if isinstance(mem, dict):
                # Debug: print what we're looking at
                    content_preview = mem.get("content", "")[:50]
                    metadata = mem.get("user_metadata", {})
                    stored_user = metadata.get("actual_user_id")
                    
                    print(f"[RETRIEVE DEBUG] Content: '{content_preview}...'")
                    print(f"[RETRIEVE DEBUG]   Metadata: {metadata}")
                    print(f"[RETRIEVE DEBUG]   Stored user: {stored_user}")
                    print(f"[RETRIEVE DEBUG]   Requested user: {user_id}")
                    print(f"[RETRIEVE DEBUG]   Match: {stored_user == user_id}")
                    
                    if stored_user == user_id:
                        filtered.append(mem)
                        print(f"[RETRIEVE DEBUG]   ✓ INCLUDED")
                    else:
                        print(f"[RETRIEVE DEBUG]   ✗ FILTERED OUT")
        
            print(f"[RETRIEVE] After filtering: {len(filtered)} memories for {user_id}")
            
            return filtered[:top_k]

        except Exception as e:
            print("[ERROR] Retrieval exception:", e)
            return []
    def retrieve_profile(self, user_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's profile memories (permanent facts)."""
        payload = {
            "session": {
                "group_id": "memorycare_group",
                "agent_id": ["memorycare_app"],
                "user_id": [user_id],
                "session_id": str(uuid.uuid4())
            },
            "query": "profile information",
            "filter": {
                "produced_for_id": user_id,
                "additionalProp1": {}
            },
            "limit": 50
        }
        
        url = f"{self.base_url}/v1/memories/profile/search"
        try:
            r = requests.post(url, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            
            # Handle various response formats similar to episodic
            if isinstance(data, dict) and "content" in data:
                if "profile_memory" in data["content"]:
                    pm = data["content"]["profile_memory"]
                    if isinstance(pm, list) and len(pm) > 1 and isinstance(pm[1], list):
                        return [m for m in pm[1] if isinstance(m, dict) and m.get("produced_for_id") == user_id]
                    elif isinstance(pm, list):
                        return [m for m in pm if isinstance(m, dict)]
            
            if isinstance(data, dict) and "results" in data:
                return [m for m in data["results"] if m.get("produced_for_id") == user_id]
            
            if isinstance(data, list):
                return [m for m in data if isinstance(m, dict) and m.get("produced_for_id") == user_id]
            
            print("[WARN] Unrecognized profile response:", data)
            return []
        except Exception as e:
            print("[ERROR] profile retrieval exception:", e)
            return []
    def store_dual_memory(self, user_id: str, episodic_text: str, profile_data: Optional[Dict[str, Any]] = None, tags: Optional[List[str]] = None):
        """
        Store information in both episodic and profile memory.
        
        Args:
            user_id: User identifier
            episodic_text: Text for episodic memory (events, conversations)
            profile_data: Dictionary of profile facts {key: value, category: str}
            tags: Tags for episodic memory
        """
        # Store episodic memory
        self.remember(user_id=user_id, text=episodic_text, tags=tags)
        
        # Store profile memory if provided
        if profile_data:
            for key, value in profile_data.items():
                if key != "category" and value:  # Skip category key and empty values
                    category = profile_data.get("category", "personal")
                    self.remember_profile(
                        user_id=user_id,
                        key=key,
                        value=str(value),
                        category=category
                    )