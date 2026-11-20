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

print("=== 1. TOP 5 RUN SCORERS ===")
cur.execute("""
SELECT player_name, team, sum(runs) as total_runs, sum(balls_faced) as balls,
       round(sum(runs)::numeric / NULLIF(sum(balls_faced), 0)::numeric * 100, 2) as sr
FROM fact_batting_scorecards
GROUP BY player_name, team
ORDER BY sum(runs) DESC
LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

print("\n=== 2. TOP 5 WICKET TAKERS ===")
cur.execute("""
SELECT player_name, team, sum(wickets) as total_wickets, sum(legal_balls) as balls,
       sum(runs_conceded) as runs_conceded,
       round(sum(runs_conceded)::numeric / (NULLIF(sum(legal_balls), 0)::numeric / 6.0), 2) as econ
FROM fact_bowling_scorecards
GROUP BY player_name, team
ORDER BY sum(wickets) DESC, econ ASC
LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

print("\n=== 3. HIGHEST STRIKE RATE (min 100 runs) ===")
cur.execute("""
SELECT player_name, team, sum(runs) as total_runs, sum(balls_faced) as balls,
       round(sum(runs)::numeric / NULLIF(sum(balls_faced), 0)::numeric * 100, 2) as sr
FROM fact_batting_scorecards
GROUP BY player_name, team
HAVING sum(runs) >= 100
ORDER BY sr DESC
LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

print("\n=== 4. BEST BOWLING ECONOMY (min 10 overs = 60 legal balls) ===")
cur.execute("""
SELECT player_name, team, sum(wickets) as total_wickets,
       round((sum(legal_balls) / 6)::numeric + (sum(legal_balls) % 6)::numeric / 10.0, 1) as overs,
       sum(runs_conceded) as runs_conceded,
       round(sum(runs_conceded)::numeric / (NULLIF(sum(legal_balls), 0)::numeric / 6.0), 2) as econ
FROM fact_bowling_scorecards
GROUP BY player_name, team
HAVING sum(legal_balls) >= 60
ORDER BY econ ASC
LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

conn.close()
