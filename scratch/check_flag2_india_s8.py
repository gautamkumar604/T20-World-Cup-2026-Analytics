import psycopg2, os
from fractions import Fraction
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

print("=== 2a. Query for total_runs = 256 ===")
cur.execute("""
SELECT s.match_id, s.batting_team, s.bowling_team, s.total_runs,
       s.total_wickets, s.legal_deliveries, m.stage, m.group_name
FROM fact_match_summaries s
JOIN dim_matches m ON s.match_id = m.match_id
WHERE s.total_runs = 256;
""")
for r in cur.fetchall():
    print(r)

print("\n=== India Super 8 Matches in dim_matches ===")
cur.execute("""
SELECT match_id, match_number, match_date, stage, group_name, team1, team2, winner, win_margin, outcome_type
FROM dim_matches
WHERE (group_name = '1' OR stage = 'Super 8')
  AND (team1 = 'India' OR team2 = 'India')
ORDER BY match_date;
""")
s8_matches = cur.fetchall()
for r in s8_matches:
    print(r)

s8_match_ids = [r[0] for r in s8_matches]

print(f"\n=== 2b. All India S8 Match Scores (match_ids: {s8_match_ids}) ===")
cur.execute(f"""
SELECT match_id, innings, batting_team, bowling_team, total_runs, total_wickets,
       legal_deliveries, is_super_over
FROM fact_match_summaries
WHERE match_id IN ({','.join(f"'{m}'" for m in s8_match_ids)})
ORDER BY match_id, innings;
""")
score_rows = cur.fetchall()
for r in score_rows:
    print(r)

# Check India's S8 Standings row from view_tournament_standings
print("\n=== India Super 8 Standings Row from view_tournament_standings ===")
cur.execute("""
SELECT stage_normalized, group_name, pool_rank, team_name, played, wins, losses, no_result,
       points, nrr_display, nrr_num, nrr_den, nrr_canon_num, nrr_canon_den,
       resolution_step
FROM view_tournament_standings
WHERE team_name = 'India' AND stage_normalized = 'Super 8';
""")
ind_standings = cur.fetchone()
print("Standings row:", ind_standings)

conn.close()
