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
SELECT match_id, match_date, match_number, stage, group_name, team1, team2
FROM dim_matches
ORDER BY match_number;
""")
rows = cur.fetchall()
print(f"Total matches: {len(rows)}")
print("Sample rows:")
for r in rows[:10]:
    print(r)
print("...")
for r in rows[-10:]:
    print(r)

print("\nCheck vw_match_results stages:")
cur.execute("SELECT stage, count(*) FROM vw_match_results GROUP BY stage;")
for r in cur.fetchall():
    print(r)

print("\nCheck vw_match_results definition:")
cur.execute("SELECT pg_get_viewdef('vw_match_results', true);")
print(cur.fetchone()[0])

conn.close()
