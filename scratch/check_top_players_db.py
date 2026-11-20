import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432'),
    dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', 'postgres')
)
cur = conn.cursor()

print("=== TOP 5 RUN SCORERS ===")
cur.execute("""
    SELECT player_name, team, SUM(runs) as total_runs, 
           ROUND(SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0) * 100, 2) as sr
    FROM fact_batting_scorecards
    GROUP BY player_name, team
    ORDER BY total_runs DESC
    LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

print("\n=== TOP 5 WICKET TAKERS ===")
cur.execute("""
    SELECT player_name, team, SUM(wickets) as total_wickets,
           ROUND(SUM(runs_conceded)::numeric / NULLIF(SUM(legal_balls)::numeric / 6.0, 0), 2) as econ
    FROM fact_bowling_scorecards
    GROUP BY player_name, team
    ORDER BY total_wickets DESC
    LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

print("\n=== HIGHEST STRIKE RATE (MIN 100 RUNS) ===")
cur.execute("""
    SELECT player_name, team, SUM(runs) as total_runs,
           ROUND(SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0) * 100, 2) as sr
    FROM fact_batting_scorecards
    GROUP BY player_name, team
    HAVING SUM(runs) >= 100
    ORDER BY sr DESC
    LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

print("\n=== BEST BOWLING ECONOMY (MIN 10 OVERS = 60 LEGAL BALLS) ===")
cur.execute("""
    SELECT player_name, team, SUM(wickets) as total_wickets,
           ROUND(SUM(runs_conceded)::numeric / (SUM(legal_balls)::numeric / 6.0), 2) as econ,
           SUM(legal_balls) as balls
    FROM fact_bowling_scorecards
    GROUP BY player_name, team
    HAVING SUM(legal_balls) >= 60
    ORDER BY econ ASC
    LIMIT 5;
""")
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
