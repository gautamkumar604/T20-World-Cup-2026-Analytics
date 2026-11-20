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

print("==================================================")
print("PHASE 4.2 DATA VALIDATION AGAINST POSTGRESQL 18.7")
print("==================================================")

# 1. KPI Banner Values
cur.execute("SELECT COUNT(*) FROM dim_matches;")
total_matches = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM dim_matches WHERE outcome_type IN ('runs', 'wickets', 'tie_super_over');")
completed_matches = cur.fetchone()[0]

cur.execute("SELECT SUM(total_runs) FROM fact_match_summaries WHERE is_super_over = FALSE;")
total_runs = cur.fetchone()[0]

cur.execute("SELECT SUM(total_wickets) FROM fact_match_summaries WHERE is_super_over = FALSE;")
total_wickets = cur.fetchone()[0]

cur.execute("""
SELECT batting_team, bowling_team, total_runs, total_wickets
FROM fact_match_summaries
WHERE is_super_over = FALSE
ORDER BY total_runs DESC
LIMIT 1;
""")
highest_row = cur.fetchone()
highest_score_str = f"{highest_row[2]}/{highest_row[3]} ({highest_row[0]} vs {highest_row[1]})"
highest_runs = highest_row[2]

cur.execute("""
SELECT batting_team, bowling_team, total_runs, total_wickets
FROM fact_match_summaries
WHERE is_super_over = FALSE
ORDER BY total_runs ASC
LIMIT 1;
""")
lowest_row = cur.fetchone()
lowest_score_str = f"{lowest_row[2]}/{lowest_row[3]} ({lowest_row[0]} vs {lowest_row[1]})"
lowest_runs = lowest_row[2]

print("1. KPI BANNER:")
print(f" - Total Matches: {total_matches}")
print(f" - Completed Matches: {completed_matches}")
print(f" - Total Runs: {total_runs}")
print(f" - Total Wickets: {total_wickets}")
print(f" - Highest Team Score: {highest_runs} | Formatted: {highest_score_str}")
print(f" - Lowest Team Score: {lowest_runs} | Formatted: {lowest_score_str}")

# 2. Tournament Progress by Stage
print("\n2. TOURNAMENT PROGRESS BY STAGE:")
cur.execute("""
SELECT CASE 
           WHEN group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
           WHEN group_name IN ('1', '2') THEN 'Super 8'
           ELSE COALESCE(stage, 'Knockout')
       END as stage_normalized,
       COUNT(*) as scheduled,
       COUNT(*) FILTER (WHERE outcome_type IN ('runs', 'wickets', 'tie_super_over')) as completed
FROM dim_matches
GROUP BY 1
ORDER BY MIN(match_date);
""")
for r in cur.fetchall():
    print(f" - {r[0]}: {r[2]} completed / {r[1]} scheduled")

# 3. Top Performers
print("\n3. TOP 5 RUN SCORERS:")
cur.execute("""
SELECT player_name, team, SUM(runs) as runs, SUM(balls_faced) as balls,
       ROUND(SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0)::numeric * 100, 2) as sr
FROM fact_batting_scorecards
GROUP BY player_name, team
ORDER BY SUM(runs) DESC
LIMIT 5;
""")
for r in cur.fetchall():
    print(f" - {r[0]} ({r[1]}): {r[2]} runs, SR {r[4]}")

print("\n4. TOP 5 WICKET TAKERS:")
cur.execute("""
SELECT player_name, team, SUM(wickets) as wkts,
       ROUND(SUM(runs_conceded)::numeric / (NULLIF(SUM(legal_balls), 0)::numeric / 6.0), 2) as econ
FROM fact_bowling_scorecards
GROUP BY player_name, team
ORDER BY SUM(wickets) DESC, econ ASC
LIMIT 5;
""")
for r in cur.fetchall():
    print(f" - {r[0]} ({r[1]}): {r[2]} wkts, Econ {r[3]}")

print("\n5. HIGHEST STRIKE RATE (min 100 runs):")
cur.execute("""
SELECT player_name, team, SUM(runs) as runs,
       ROUND(SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0)::numeric * 100, 2) as sr
FROM fact_batting_scorecards
GROUP BY player_name, team
HAVING SUM(runs) >= 100
ORDER BY sr DESC
LIMIT 5;
""")
for r in cur.fetchall():
    print(f" - {r[0]} ({r[1]}): {r[3]} SR ({r[2]} runs)")

print("\n6. BEST BOWLING ECONOMY (min 10 overs = 60 balls):")
cur.execute("""
SELECT player_name, team, SUM(wickets) as wkts,
       ROUND((SUM(legal_balls)/6)::numeric + (SUM(legal_balls)%6)::numeric/10.0, 1) as overs,
       ROUND(SUM(runs_conceded)::numeric / (NULLIF(SUM(legal_balls), 0)::numeric / 6.0), 2) as econ
FROM fact_bowling_scorecards
GROUP BY player_name, team
HAVING SUM(legal_balls) >= 60
ORDER BY econ ASC
LIMIT 5;
""")
for r in cur.fetchall():
    print(f" - {r[0]} ({r[1]}): {r[4]} Econ ({r[3]} overs, {r[2]} wkts)")

print("\n7. VENUE FIRST INNINGS AVERAGES:")
cur.execute("""
SELECT m.venue,
       COUNT(DISTINCT m.match_id) as matches,
       ROUND(AVG(CASE WHEN s.innings = 1 THEN s.total_runs END), 1) as avg_1st
FROM dim_matches m
JOIN fact_match_summaries s ON m.match_id = s.match_id
WHERE s.is_super_over = FALSE
GROUP BY m.venue
ORDER BY avg_1st DESC;
""")
for r in cur.fetchall():
    print(f" - {r[0]}: {r[2]} avg 1st inn ({r[1]} matches)")

conn.close()
