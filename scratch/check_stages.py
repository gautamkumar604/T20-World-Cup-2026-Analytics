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

cur.execute("SELECT stage, COUNT(*) FROM dim_matches GROUP BY stage ORDER BY stage;")
print("dim_matches stages:")
for r in cur.fetchall():
    print(r)

cur.execute("""
SELECT stage, COUNT(*) as total_matches,
       COUNT(*) FILTER (WHERE outcome_type IN ('runs', 'wickets', 'tie_super_over')) as completed_matches,
       COUNT(*) FILTER (WHERE outcome_type = 'no result') as abandoned_matches
FROM dim_matches
GROUP BY stage
ORDER BY MIN(match_date);
""")
print("\nStage breakdown:")
for r in cur.fetchall():
    print(r)

conn.close()
