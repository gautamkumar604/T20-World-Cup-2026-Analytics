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
SELECT DISTINCT b.team, t.team_name
FROM fact_batting_scorecards b
LEFT JOIN dim_teams t ON b.team = t.team_name
WHERE t.team_name IS NULL;
""")
unmatched_bat = cur.fetchall()
print(f"Unmatched batting teams in dim_teams: {len(unmatched_bat)}")

cur.execute("""
SELECT DISTINCT bw.team, t.team_name
FROM fact_bowling_scorecards bw
LEFT JOIN dim_teams t ON bw.team = t.team_name
WHERE t.team_name IS NULL;
""")
unmatched_bowl = cur.fetchall()
print(f"Unmatched bowling teams in dim_teams: {len(unmatched_bowl)}")

conn.close()
