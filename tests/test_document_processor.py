"""Tests for document_processor utility functions.
These tests do not call Claude — they test local processing logic only.
"""
import pytest


def test_markdown_fence_stripping():
    """Verify JSON wrapped in code fences is cleaned correctly.
    Tests all fence variants Claude might produce despite being told not to."""
    from api.services.document_processor import strip_json_fences

    raw_json = '[{"signal_name": "test", "domain": "Delivery Operations"}]'

    # No fences — should pass through unchanged
    assert strip_json_fences(raw_json) == raw_json

    # ```json fence
    fenced_json = f'```json\n{raw_json}\n```'
    assert strip_json_fences(fenced_json) == raw_json

    # plain ``` fence
    fenced_plain = f'```\n{raw_json}\n```'
    assert strip_json_fences(fenced_plain) == raw_json

    # Extra whitespace
    fenced_whitespace = f'  ```json\n{raw_json}\n```  '
    assert strip_json_fences(fenced_whitespace) == raw_json


def test_file_type_detection():
    """Verify get_file_type correctly identifies file types from filename."""
    from api.services.document_processor import get_file_type

    assert get_file_type('E001_interview_CEO_Okafor.txt')        == 'interview'
    assert get_file_type('E001_financial_FY2025_PL.txt')         == 'financial'
    assert get_file_type('E001_sow_ProjectAlpha.txt')            == 'sow'
    assert get_file_type('E001_portfolio_March.txt')             == 'portfolio'
    assert get_file_type('E001_status_ProjectAlpha_March.txt')   == 'status'
    assert get_file_type('E001_resource_utilization_Q1.txt')     == 'resource'
    assert get_file_type('E001_delivery_risk_register.txt')      == 'delivery'
    assert get_file_type('E001_other_misc.txt')                  == 'other'
    assert get_file_type('E001_unknown_type_file.txt')           == 'other'
    # Type with uppercase — should normalize to lowercase
    assert get_file_type('E001_INTERVIEW_CEO.txt')               == 'interview'


def test_valid_domains_in_utils():
    """Verify domains.py contains exactly the expected 10 domains."""
    from api.utils.domains import VALID_DOMAINS

    expected = {
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
    assert VALID_DOMAINS == expected, (
        f"Domain mismatch: {VALID_DOMAINS.symmetric_difference(expected)}"
    )


def test_valid_confidences_in_utils():
    """Verify domains.py contains the correct confidence values."""
    from api.utils.domains import VALID_CONFIDENCES

    assert 'High' in VALID_CONFIDENCES
    assert 'Medium' in VALID_CONFIDENCES
    assert 'Hypothesis' in VALID_CONFIDENCES
    assert len(VALID_CONFIDENCES) == 3
