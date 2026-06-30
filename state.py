"""
Shared state module for Nandi AI Bot and Admin Dashboard.
"""

# ─── Available Models ──────────────────────────────────────────────────────────
MODELS: dict[str, dict] = {
    "1": {
        "id": "llama-3.3-70b-versatile",
        "label": "LLaMA 3.3 70B Versatile",
        "description": "Most capable — best for complex reasoning and detailed answers",
    },
    "2": {
        "id": "llama-3.1-8b-instant",
        "label": "LLaMA 3.1 8B Instant",
        "description": "Lightweight & fast — best for quick, snappy replies",
    },
}

DEFAULT_MODEL_KEY = "1"

# ─── In-memory state ─────────────────────────────────────────────────────────
conversation_histories: dict[int, list[dict]] = {}
user_model_keys: dict[int, str] = {}

total_messages_received: int = 0
active_users: set[int] = set()
all_users: set[int] = set()
errors_count: int = 0
user_feedbacks: list[dict] = []
