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
SELECT match_id, team1, team2, stage, outcome_type, winner, win_margin
FROM dim_matches
WHERE outcome_type = 'no result' OR winner IS NULL;
""")
rows = cur.fetchall()
print("Matches with outcome_type = 'no result' or winner is null:")
for r in rows:
    print(r)

cur.execute("SELECT DISTINCT winner FROM dim_matches;")
print("\nDistinct winners in dim_matches:")
for r in cur.fetchall():
    print(r)

print("\nHighest and lowest team scores in fact_match_summaries:")
cur.execute("""
SELECT batting_team, bowling_team, total_runs, total_wickets, legal_deliveries, is_super_over
FROM fact_match_summaries
WHERE total_runs IN (
    (SELECT MAX(total_runs) FROM fact_match_summaries),
    (SELECT MIN(total_runs) FROM fact_match_summaries)
);
""")
for r in cur.fetchall():
    print(r)

conn.close()
