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

# Task 9 queries
print("=== TASK 9 PSQL QUERIES ===")
cur.execute("SELECT COUNT(*) FROM dim_matches;")
print(f"Total Matches: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM dim_matches WHERE winner IS NOT NULL;")
print(f"Matches Completed (winner is not null): {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM dim_matches WHERE outcome_type IN ('runs', 'wickets', 'tie_super_over');")
print(f"Matches Completed (outcome_type in runs, wickets, tie_super_over): {cur.fetchone()[0]}")

cur.execute("SELECT SUM(total_runs) FROM fact_match_summaries;")
print(f"Total Runs Scored (all fact_match_summaries): {cur.fetchone()[0]}")

cur.execute("SELECT SUM(total_runs) FROM fact_match_summaries WHERE is_super_over = FALSE;")
print(f"Total Runs Scored (excl super over): {cur.fetchone()[0]}")

cur.execute("SELECT SUM(total_wickets) FROM fact_match_summaries WHERE is_super_over = FALSE;")
print(f"Total Wickets (excl super over): {cur.fetchone()[0]}")

cur.execute("SELECT MAX(total_runs) FROM fact_match_summaries;")
print(f"MAX(total_runs) from fact_match_summaries: {cur.fetchone()[0]}")

cur.execute("""
SELECT batting_team, bowling_team, total_runs, total_wickets, overs
FROM fact_match_summaries
WHERE total_runs = (SELECT MAX(total_runs) FROM fact_match_summaries);
""")
print(f"Highest Team Score row: {cur.fetchall()}")

cur.execute("SELECT MIN(total_runs) FROM fact_match_summaries WHERE is_super_over = FALSE;")
print(f"MIN(total_runs) from fact_match_summaries (excl super over): {cur.fetchone()[0]}")

cur.execute("""
SELECT batting_team, bowling_team, total_runs, total_wickets, overs
FROM fact_match_summaries
WHERE total_runs = (SELECT MIN(total_runs) FROM fact_match_summaries WHERE is_super_over = FALSE);
""")
print(f"Lowest Team Score row (excl super over): {cur.fetchall()}")

# Let's also check if super overs are included in MIN
cur.execute("SELECT MIN(total_runs) FROM fact_match_summaries;")
print(f"MIN(total_runs) all: {cur.fetchone()[0]}")
cur.execute("""
SELECT batting_team, bowling_team, total_runs, total_wickets, is_super_over
FROM fact_match_summaries
WHERE total_runs = (SELECT MIN(total_runs) FROM fact_match_summaries);
""")
print(f"Lowest Team Score row all: {cur.fetchall()}")

conn.close()
