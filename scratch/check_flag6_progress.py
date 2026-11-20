import psycopg2, os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', 'postgres'),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

print("=== Unfiltered Slicer Behavior (All Teams) ===")
cur.execute("""
WITH bridge AS (
    SELECT match_id, team1 as team_name, outcome_type FROM dim_matches
    UNION ALL
    SELECT match_id, team2 as team_name, outcome_type FROM dim_matches
)
SELECT CASE 
           WHEN m.group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
           WHEN m.group_name IN ('1', '2') THEN 'Super 8'
           ELSE COALESCE(m.stage, 'Knockout')
       END as stage_normalized,
       COUNT(DISTINCT b.match_id) as completed_matches
FROM dim_matches m
JOIN bridge b ON m.match_id = b.match_id
WHERE b.outcome_type != 'no result'
GROUP BY 1
ORDER BY MIN(m.match_date);
""")
for r in cur.fetchall():
    print(f" - {r[0]}: {r[1]} matches")

print("\n=== Filtered Slicer Behavior (Team = 'India') ===")
cur.execute("""
WITH bridge AS (
    SELECT match_id, team1 as team_name, outcome_type FROM dim_matches
    UNION ALL
    SELECT match_id, team2 as team_name, outcome_type FROM dim_matches
)
SELECT CASE 
           WHEN m.group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
           WHEN m.group_name IN ('1', '2') THEN 'Super 8'
           ELSE COALESCE(m.stage, 'Knockout')
       END as stage_normalized,
       COUNT(DISTINCT b.match_id) as completed_matches
FROM dim_matches m
JOIN bridge b ON m.match_id = b.match_id
WHERE b.outcome_type != 'no result'
  AND b.team_name = 'India'
GROUP BY 1
ORDER BY MIN(m.match_date);
""")
for r in cur.fetchall():
    print(f" - {r[0]}: {r[1]} matches")

conn.close()
