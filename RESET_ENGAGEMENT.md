# Resetting an Engagement for Reprocessing

Use this when you need to wipe an engagement's data and start over from scratch
(e.g., after schema changes, prompt changes, or bad signal extractions).

---

## Step 1 — Delete database rows

Open TOP.db in DB Browser for SQLite. Run the following SQL, replacing `E00X` and `C00X`
with the engagement and client IDs you are resetting.

Run in this order (children before parents):

```sql
DELETE FROM SignalCoverage      WHERE engagement_id = 'E00X';
DELETE FROM Signals             WHERE engagement_id = 'E00X';
DELETE FROM ProcessedFiles      WHERE engagement_id = 'E00X';
DELETE FROM EngagementPatterns  WHERE engagement_id = 'E00X';
DELETE FROM AgentRuns           WHERE engagement_id = 'E00X';
DELETE FROM OPDFindings         WHERE engagement_id = 'E00X';
DELETE FROM RoadmapItems        WHERE engagement_id = 'E00X';
DELETE FROM KnowledgePromotions WHERE engagement_id = 'E00X';
DELETE FROM Engagements         WHERE engagement_id = 'E00X';
DELETE FROM Clients             WHERE client_id     = 'C00X';
```

Tables that are almost always empty for a fresh engagement and can be skipped if you
prefer: `Interviews`, `Documents`. Check with `SELECT COUNT(*) FROM Interviews WHERE engagement_id = 'E00X'` if unsure.

---

## Step 2 — Delete candidate JSON files

Navigate to the engagement's `05_Candidates` folder (path is stored in
`Engagements.candidates_folder`).

Delete:
- All `*_candidates.json` files in the root of the folder
- All `*_candidates.json` files in the `processed\` subfolder (archived copies from prior load runs)
- The `processed\` subfolder itself if you want a clean slate

The `archive\` subfolder can be left alone — it is usually empty.

---

## Step 3 — Re-create the engagement

After wiping, create a new engagement through the UI. The next available ID will be
auto-assigned (MAX+1). Re-enter the folder paths in Engagement Settings.

If you want to reuse the same engagement ID (e.g., keep E004), skip Step 1's final two
`DELETE` statements (Engagements + Clients) and re-enter only the data rows, not the
engagement record itself. The folder paths and client details will still be present.

---

## Finding the client ID for an engagement

```sql
SELECT engagement_id, client_id, engagement_name FROM Engagements WHERE engagement_id = 'E00X';
```

---

## Quick row-count audit before deleting

Run this to see what you are about to remove:

```sql
SELECT 'Signals'             AS tbl, COUNT(*) FROM Signals             WHERE engagement_id = 'E00X'
UNION ALL
SELECT 'ProcessedFiles',              COUNT(*) FROM ProcessedFiles      WHERE engagement_id = 'E00X'
UNION ALL
SELECT 'SignalCoverage',              COUNT(*) FROM SignalCoverage      WHERE engagement_id = 'E00X'
UNION ALL
SELECT 'EngagementPatterns',          COUNT(*) FROM EngagementPatterns  WHERE engagement_id = 'E00X'
UNION ALL
SELECT 'AgentRuns',                   COUNT(*) FROM AgentRuns           WHERE engagement_id = 'E00X'
UNION ALL
SELECT 'OPDFindings',                 COUNT(*) FROM OPDFindings         WHERE engagement_id = 'E00X'
UNION ALL
SELECT 'RoadmapItems',                COUNT(*) FROM RoadmapItems        WHERE engagement_id = 'E00X'
UNION ALL
SELECT 'KnowledgePromotions',         COUNT(*) FROM KnowledgePromotions WHERE engagement_id = 'E00X';
```
