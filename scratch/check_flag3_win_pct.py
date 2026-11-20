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

# Check England Super 8
cur.execute("""
SELECT m.match_id, m.match_date, m.team1, m.team2, m.winner, m.outcome_type
FROM dim_matches m
WHERE (m.group_name = '2' OR m.stage = 'Super 8')
  AND (m.team1 = 'England' OR m.team2 = 'England');
""")
print("=== England Super 8 Matches ===")
for r in cur.fetchall():
    print(r)

# Check all teams in Super 8
cur.execute("""
SELECT t.team_name,
       COUNT(*) as played,
       COUNT(*) FILTER (WHERE m.winner = t.team_name) as wins,
       COUNT(*) FILTER (WHERE m.outcome_type = 'no result') as no_results
FROM dim_matches m
JOIN (
    SELECT match_id, team1 as team_name FROM dim_matches
    UNION ALL
    SELECT match_id, team2 as team_name FROM dim_matches
) t ON m.match_id = t.match_id
WHERE m.group_name IN ('1', '2')
GROUP BY t.team_name
ORDER BY t.team_name;
""")
print("\n=== Super 8 Team Records ===")
for r in cur.fetchall():
    played, wins, nr = r[1], r[2], r[3]
    pct_played = (wins / played) * 100
    pct_completed = (wins / (played - nr)) * 100 if (played - nr) > 0 else 0
    print(f"{r[0]:<15} | Played: {played} | Wins: {wins} | NR: {nr} | Wins/Played: {pct_played:5.1f}% | Wins/(Played-NR): {pct_completed:5.1f}%")

conn.close()
