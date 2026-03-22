# TOP Configuration
# TunTech Operations Platform - Phase 1
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(r"C:\Users\varic\OneDrive\100_TunTech\TOP")

# Database — string for sqlite3 compatibility
DB_PATH = r"C:\Users\varic\OneDrive\100_TunTech\TOP\TOP.db"

# Reports output folder — Path object so mkdir works
REPORTS_DIR = Path(r"C:\Users\varic\OneDrive\100_TunTech\TOP\reports")

# Ensure reports directory exists
REPORTS_DIR.mkdir(exist_ok=True)

# Agent names - valid values for log-agent-run command
VALID_AGENTS = [
    "Diagnostician",
    "Delivery",
    "Economics",
    "Skeptic",
    "Synthesizer"
]

# Domain list - used in populate-findings command
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