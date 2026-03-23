import sqlite3
import pytest
import os
from pathlib import Path

TEST_DB = Path("test.db")


def setup_test_db():
    """Create a minimal test database with all required tables."""
    conn = sqlite3.connect(TEST_DB)
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
            created_date TEXT NOT NULL
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
            created_date TEXT NOT NULL
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
            prompt_version TEXT,
            output_summary TEXT,
            output_doc_link TEXT,
            accepted INTEGER DEFAULT 0,
            created_date TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def teardown_test_db():
    """Remove the test database — use missing_ok to handle Windows file locks."""
    try:
        TEST_DB.unlink(missing_ok=True)
    except PermissionError:
        pass


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
            created_date TEXT NOT NULL
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
            created_date TEXT NOT NULL
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
            prompt_version TEXT,
            output_summary TEXT,
            output_doc_link TEXT,
            accepted INTEGER DEFAULT 0,
            created_date TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

    import importlib
    import config
    importlib.reload(config)

    yield


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

    base        = BaseRepository()
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
