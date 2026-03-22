from api.db.repositories.base import BaseRepository

r = BaseRepository()
rows = r._query("SELECT * FROM vw_OPDSummary LIMIT 1")
for row in rows:
    print(dict(row))