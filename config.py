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

# Claude model — change here or via environment variable
MODEL = os.environ.get("TOP_MODEL", "claude-sonnet-4-6")

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