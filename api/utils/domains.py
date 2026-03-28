"""
Single source of truth for valid domain and enumeration values.
Import from here in document_processor.py, patterns.py, and any
new code that needs to validate domains or confidences.
Frontend equivalent: src/constants.js (keep in sync manually).
"""

VALID_DOMAINS = {
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
}

VALID_CONFIDENCES = {'High', 'Medium', 'Hypothesis'}

VALID_SIGNAL_SOURCES = {'Interview', 'Document', 'Observation'}

VALID_PRIORITIES = {'High', 'Medium', 'Low'}

VALID_EFFORTS = {'High', 'Medium', 'Low'}

VALID_PHASES = {'Stabilize', 'Optimize', 'Scale'}

VALID_FINDING_CONFIDENCES = {'High', 'Medium', 'Low'}
