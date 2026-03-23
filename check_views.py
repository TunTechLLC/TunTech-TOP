from api.db.repositories.reporting import ReportingRepository

r = ReportingRepository()

tests = [
    ('pattern_frequency',           r.get_pattern_frequency),
    ('pattern_frequency_by_domain', r.get_pattern_frequency_by_domain),
    ('accepted_patterns',           r.get_accepted_patterns),
    ('economic_impact',             r.get_economic_impact),
    ('agent_run_log',               r.get_agent_run_log),
    ('engagement_summary',          r.get_engagement_summary),
    ('engagement_overview',         r.get_engagement_overview),
]

for name, fn in tests:
    try:
        rows = fn()
        print(f"OK  {name}: {len(rows)} rows")
    except Exception as e:
        print(f"ERR {name}: {e}")
