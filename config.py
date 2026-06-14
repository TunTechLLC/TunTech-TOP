import os

# Database path — overridable for testing and Phase 3 migration
DB_PATH = os.environ.get(
    "TOP_DB_PATH",
    r"C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db"
)

# Log file path
LOG_PATH = os.environ.get(
    "TOP_LOG_PATH",
    r"C:\Dev\TunTech\TOP\top.log"
)

# Claude model — change here or via environment variable.
# Standardized on Opus 4.7 (2026-06-14). The 4 QA constants in claude.py are also
# 4.7, so the whole system runs 4.7. Requires streaming in the long Claude calls
# (see _stream_final_message in claude.py) — Opus exceeds the non-streaming timeout.
MODEL = os.environ.get("TOP_MODEL", "claude-opus-4-7")

# Max tokens per Claude call
MAX_TOKENS = int(os.environ.get("TOP_MAX_TOKENS", "8000"))

# Valid domains — single source of truth for backend
# Frontend uses src/constants.js (kept in sync)
DOMAINS = [
    'Sales & Pipeline',
    'Sales-to-Delivery Transition',
    'Delivery Operations',
    'Resource Management',
    'Project Governance / PMO',
    'Consulting Economics',
    'Customer Experience',
    'AI Readiness',
    'Human Resources',
    'Finance and Commercial',
]