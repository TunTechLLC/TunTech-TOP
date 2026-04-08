import sqlite3
import pytest
import os
from pathlib import Path


@pytest.fixture(autouse=True)
def test_db(monkeypatch, tmp_path):
    """Set up and tear down test database for each test.
    Uses tmp_path to get a unique path per test — avoids Windows file lock issues."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("TOP_DB_PATH", str(db_path))

    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS Clients (
            client_id TEXT PRIMARY KEY,
            firm_name TEXT NOT NULL,
            firm_size INTEGER,
            service_model TEXT,
            notes TEXT,
            created_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Engagements (
            engagement_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            engagement_name TEXT NOT NULL,
            status TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT,
            engagement_type TEXT,
            stated_problem TEXT,
            client_hypothesis TEXT,
            previously_tried TEXT,
            notes TEXT,
            created_date TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES Clients(client_id)
        );
        CREATE TABLE IF NOT EXISTS Signals (
            signal_id TEXT PRIMARY KEY,
            engagement_id TEXT NOT NULL,
            interview_id TEXT,
            signal_name TEXT NOT NULL,
            domain TEXT,
            observed_value TEXT,
            normalized_band TEXT,
            signal_confidence TEXT,
            economic_relevance TEXT,
            source TEXT,
            notes TEXT,
            created_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS Patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_name TEXT,
            domain TEXT,
            trigger_signals TEXT,
            operational_impact TEXT,
            likely_root_cause TEXT,
            recommended_improvements TEXT,
            economic_model TEXT,
            economic_formula TEXT
        );
        CREATE TABLE IF NOT EXISTS EngagementPatterns (
            ep_id TEXT PRIMARY KEY,
            engagement_id TEXT NOT NULL,
            pattern_id TEXT,
            confidence TEXT,
            economic_impact_est TEXT,
            accepted INTEGER DEFAULT 0,
            notes TEXT,
            created_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS OPDFindings (
            finding_id TEXT PRIMARY KEY,
            engagement_id TEXT NOT NULL,
            pattern_id TEXT,
            finding_title TEXT NOT NULL,
            domain TEXT,
            confidence TEXT,
            operational_impact TEXT,
            economic_impact TEXT,
            root_cause TEXT,
            recommendation TEXT,
            priority TEXT,
            effort TEXT,
            opd_section INTEGER,
            created_date TEXT NOT NULL,
            evidence_summary TEXT,
            key_quotes TEXT
        );
        CREATE TABLE IF NOT EXISTS RoadmapItems (
            item_id TEXT PRIMARY KEY,
            engagement_id TEXT NOT NULL,
            finding_id TEXT,
            initiative_name TEXT NOT NULL,
            domain TEXT,
            phase TEXT,
            priority TEXT,
            effort TEXT,
            estimated_impact TEXT,
            owner TEXT,
            target_date TEXT,
            status TEXT,
            created_date TEXT NOT NULL,
            capability TEXT,
            addressing_finding_ids TEXT,
            depends_on TEXT
        );
        CREATE TABLE IF NOT EXISTS KnowledgePromotions (
            promotion_id TEXT PRIMARY KEY,
            engagement_id TEXT NOT NULL,
            finding_id TEXT,
            pattern_id TEXT,
            promotion_type TEXT NOT NULL,
            description TEXT NOT NULL,
            applied_to TEXT,
            promotion_date TEXT NOT NULL,
            created_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS AgentRuns (
            run_id TEXT PRIMARY KEY,
            engagement_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            model_used TEXT,
            run_date TEXT,
            output_summary TEXT,
            output_full TEXT,
            output_doc_link TEXT,
            accepted INTEGER DEFAULT 0,
            created_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ProcessedFiles (
            file_id TEXT PRIMARY KEY,
            engagement_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            file_type TEXT NOT NULL,
            processed_date TEXT NOT NULL,
            signal_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'processed',
            UNIQUE(file_hash)
        );
    """)
    conn.commit()
    conn.close()

    import importlib
    import config
    importlib.reload(config)

    yield


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

def test_engagement_repository_create_and_retrieve():
    """Repository integration test — create an engagement and read it back."""
    from api.db.repositories.engagement import EngagementRepository

    repo = EngagementRepository()
    data = {
        'firm_name':         'Test Firm',
        'firm_size':         50,
        'service_model':     'IT Consulting',
        'stated_problem':    'Test problem',
        'client_hypothesis': 'Test hypothesis',
        'previously_tried':  'Nothing',
    }

    engagement_id = repo.create(data)

    assert engagement_id is not None
    assert engagement_id.startswith('E')

    result = repo.get_by_id(engagement_id)
    assert result is not None
    assert result['firm_name'] == 'Test Firm'
    assert result['status'] == 'Active'

    all_engagements = repo.get_all()
    ids = [e['engagement_id'] for e in all_engagements]
    assert engagement_id in ids


def test_finding_repository_atomic_transaction():
    """Transaction test — finding creation and pattern acceptance are atomic."""
    from api.db.repositories.base import BaseRepository
    from api.db.repositories.finding import FindingRepository

    base         = BaseRepository()
    finding_repo = FindingRepository()

    base._write(
        "INSERT INTO EngagementPatterns VALUES (?,?,?,?,NULL,0,?,?)",
        ('EP_TEST', 'E_TEST', 'P38', 'High', 'test notes', '2026-03-23')
    )

    pattern_before = base._query(
        "SELECT accepted FROM EngagementPatterns WHERE ep_id = ?",
        ('EP_TEST',)
    )
    assert pattern_before[0]['accepted'] == 0

    finding_data = {
        'finding_title':      'Test Finding',
        'domain':             'Consulting Economics',
        'confidence':         'High',
        'operational_impact': 'Test operational impact',
        'economic_impact':    'Test economic impact',
        'root_cause':         'Test root cause',
        'recommendation':     'Test recommendation',
        'priority':           'High',
        'effort':             'Medium',
    }

    finding_id = finding_repo.create('E_TEST', finding_data, ['EP_TEST'])
    assert finding_id is not None

    pattern_after = base._query(
        "SELECT accepted FROM EngagementPatterns WHERE ep_id = ?",
        ('EP_TEST',)
    )
    assert pattern_after[0]['accepted'] == 1

    findings = finding_repo.get_all('E_TEST')
    assert len(findings) == 1
    assert findings[0]['finding_title'] == 'Test Finding'


# ---------------------------------------------------------------------------
# Phase 8 tests
# ---------------------------------------------------------------------------

def test_pattern_bulk_create_sequential_ids():
    """Verify bulk_create generates unique sequential EP IDs.
    Regression test for the duplicate ID bug — was using list comprehension
    which called next_ep_id() before any rows were written."""
    from api.db.repositories.engagement import EngagementRepository
    from api.db.repositories.pattern import PatternRepository
    from api.db.repositories.base import BaseRepository

    # Insert a test pattern into the library so the FK is valid
    base = BaseRepository()
    base._write(
        "INSERT INTO Patterns (pattern_id, pattern_name, domain) VALUES (?,?,?)",
        ('P12', 'Test Pattern 12', 'Delivery Operations')
    )
    base._write(
        "INSERT INTO Patterns (pattern_id, pattern_name, domain) VALUES (?,?,?)",
        ('P27', 'Test Pattern 27', 'Consulting Economics')
    )
    base._write(
        "INSERT INTO Patterns (pattern_id, pattern_name, domain) VALUES (?,?,?)",
        ('P38', 'Test Pattern 38', 'Resource Management')
    )

    # Create an engagement to use as FK
    eng_repo = EngagementRepository()
    engagement_id = eng_repo.create({
        'firm_name':         'Test Firm',
        'firm_size':         50,
        'service_model':     'IT Consulting',
        'stated_problem':    'Test',
        'client_hypothesis': '',
        'previously_tried':  '',
    })

    pattern_repo = PatternRepository()
    rows = [
        {'engagement_id': engagement_id, 'pattern_id': 'P12', 'confidence': 'High',   'notes': 'test1'},
        {'engagement_id': engagement_id, 'pattern_id': 'P27', 'confidence': 'Medium', 'notes': 'test2'},
        {'engagement_id': engagement_id, 'pattern_id': 'P38', 'confidence': 'High',   'notes': 'test3'},
    ]
    pattern_repo.bulk_create(rows)

    patterns = pattern_repo.get_for_engagement(engagement_id)
    ep_ids   = [p['ep_id'] for p in patterns]

    assert len(ep_ids) == 3, f"Expected 3 patterns, got {len(ep_ids)}"
    assert len(ep_ids) == len(set(ep_ids)), f"Duplicate EP IDs generated: {ep_ids}"


def test_agent_run_prerequisites_blocking():
    """Verify validate_prerequisites blocks agents when required agents not accepted."""
    from api.db.repositories.engagement import EngagementRepository
    from api.db.repositories.agent_run import AgentRunRepository

    eng_repo = EngagementRepository()
    engagement_id = eng_repo.create({
        'firm_name':         'Test Firm',
        'firm_size':         50,
        'service_model':     'IT Consulting',
        'stated_problem':    'Test',
        'client_hypothesis': '',
        'previously_tried':  '',
    })

    agent_repo = AgentRunRepository()

    # No agents run yet — all three prerequisites should be missing
    missing = agent_repo.validate_prerequisites(
        engagement_id,
        ['Diagnostician', 'Delivery Operations', 'Consulting Economics']
    )
    assert 'Diagnostician' in missing
    assert 'Delivery Operations' in missing
    assert 'Consulting Economics' in missing

    # Create and accept a Diagnostician run
    run_id = agent_repo.create({
        'engagement_id':  engagement_id,
        'agent_name':     'Diagnostician',
        'output_full':    'Full test output for Diagnostician',
        'output_summary': 'Test summary',
        'model_used':     'claude-sonnet-4-6',
    })
    agent_repo.accept(run_id)

    # Now only Delivery Operations and Consulting Economics should be missing
    missing = agent_repo.validate_prerequisites(
        engagement_id,
        ['Diagnostician', 'Delivery Operations', 'Consulting Economics']
    )
    assert 'Diagnostician' not in missing
    assert 'Delivery Operations' in missing
    assert 'Consulting Economics' in missing


def test_pattern_detection_result_validators():
    """Verify Pydantic validators reject invalid pattern_ids and confidence values."""
    from api.models.pattern import PatternDetectionResult

    # Valid data should pass
    valid = PatternDetectionResult(pattern_id='P12', confidence='High', notes='test')
    assert valid.pattern_id == 'P12'
    assert valid.confidence == 'High'

    # Valid hypothesis confidence should pass
    valid2 = PatternDetectionResult(pattern_id='P5', confidence='Hypothesis', notes='weak signal')
    assert valid2.confidence == 'Hypothesis'

    # Invalid pattern_id format should raise
    with pytest.raises(Exception):
        PatternDetectionResult(pattern_id='INVALID', confidence='High', notes='test')

    # Invalid confidence value should raise
    with pytest.raises(Exception):
        PatternDetectionResult(pattern_id='P12', confidence='Excellent', notes='test')

    # Non-P prefix should raise
    with pytest.raises(Exception):
        PatternDetectionResult(pattern_id='EP012', confidence='High', notes='test')
