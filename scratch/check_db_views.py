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

views = ['vw_top_run_scorers', 'vw_top_wicket_takers', 'vw_venue_analysis']
for v in views:
    cur.execute(f"SELECT pg_get_viewdef('{v}', true);")
    print(f"=== {v} ===")
    print(cur.fetchone()[0])
    print()

conn.close()
