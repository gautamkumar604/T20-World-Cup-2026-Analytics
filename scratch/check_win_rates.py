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

cur.execute("""
WITH match_stages AS (
    SELECT match_id,
           CASE 
               WHEN group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
               WHEN group_name IN ('1', '2') THEN 'Super 8'
               ELSE COALESCE(stage, 'Knockout')
           END as stage_normalized,
           winner,
           outcome_type
    FROM dim_matches
),
team_matches AS (
    SELECT m.match_id,
           m.stage_normalized,
           t.team_name,
           (m.winner = t.team_name) as is_winner,
           (m.outcome_type = 'no result') as is_no_result
    FROM match_stages m
    JOIN (
        SELECT match_id, team1 as team_name FROM dim_matches
        UNION ALL
        SELECT match_id, team2 as team_name FROM dim_matches
    ) t ON m.match_id = t.match_id
),
team_stats AS (
    SELECT team_name,
           stage_normalized,
           COUNT(*) as played,
           COUNT(*) FILTER (WHERE is_winner) as wins,
           COUNT(*) FILTER (WHERE is_no_result) as no_results,
           ROUND(COUNT(*) FILTER (WHERE is_winner)::numeric / NULLIF(COUNT(*) FILTER (WHERE NOT is_no_result), 0) * 100, 1) as win_pct
    FROM team_matches
    GROUP BY team_name, stage_normalized
),
total_wins_per_team AS (
    SELECT team_name, SUM(wins) as total_wins
    FROM team_stats
    GROUP BY team_name
)
SELECT s.team_name, s.stage_normalized, s.played, s.wins, s.no_results, s.win_pct, w.total_wins
FROM team_stats s
JOIN total_wins_per_team w ON s.team_name = w.team_name
WHERE w.total_wins >= 1
ORDER BY w.total_wins DESC, s.team_name, s.stage_normalized;
""")
print("=== TEAM WIN RATE BY STAGE (Teams with >= 1 win) ===")
rows = cur.fetchall()
for r in rows:
    print(r)

conn.close()
