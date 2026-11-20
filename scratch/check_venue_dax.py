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
SELECT m.venue,
       COUNT(DISTINCT m.match_id) as matches,
       ROUND(AVG(CASE WHEN s.innings = 1 THEN s.total_runs END), 1) as avg_1st_inn,
       ROUND(AVG(CASE WHEN s.innings = 2 THEN s.total_runs END), 1) as avg_2nd_inn
FROM dim_matches m
JOIN fact_match_summaries s ON m.match_id = s.match_id
WHERE s.is_super_over = FALSE
GROUP BY m.venue
ORDER BY avg_1st_inn DESC;
""")
print("=== DAX CALCULATION CHECK ON FACT_MATCH_SUMMARIES BY VENUE ===")
for r in cur.fetchall():
    print(r)

conn.close()
