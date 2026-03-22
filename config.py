# TOP Configuration
# TunTech Operations Platform - Phase 2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database — loaded from .env
DB_PATH = os.getenv('TOP_DB_PATH', r'C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db')

# Reports output folder — loaded from .env
REPORTS_DIR = Path(os.getenv('REPORTS_DIR', r'C:\Users\varic\OneDrive\100_TunTech\TOP\reports'))

# Ensure reports directory exists
REPORTS_DIR.mkdir(exist_ok=True)

# Agent names
VALID_AGENTS = [
    "Diagnostician",
    "Delivery",
    "Economics",
    "Skeptic",
    "Synthesizer"
]

# Domain list
DOMAINS = [
    "Sales & Pipeline",
    "Sales-to-Delivery Transition",
    "Delivery Operations",
    "Resource Management",
    "Project Governance / PMO",
    "Consulting Economics",
    "Customer Experience"
]

# Confidence levels
CONFIDENCE_LEVELS = ["High", "Medium", "Hypothesis"]

# Roadmap phases
ROADMAP_PHASES = ["Stabilize", "Optimize", "Scale"]

# Priority levels
PRIORITY_LEVELS = ["High", "Medium", "Low"]
