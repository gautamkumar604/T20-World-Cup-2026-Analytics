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
SELECT venue_name, city, total_matches_scheduled, matches_completed, avg_first_innings_score, avg_second_innings_score
FROM vw_venue_analysis
ORDER BY total_matches_scheduled DESC;
""")
print("=== VENUE ANALYSIS ===")
for r in cur.fetchall():
    print(r)

# Check pace vs spin in fact_deliveries
cur.execute("""
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'fact_deliveries'
AND column_name LIKE '%bowling%' OR column_name LIKE '%spin%' OR column_name LIKE '%pace%';
""")
print("\nSpin/Pace columns in fact_deliveries:")
for r in cur.fetchall():
    print(r)

cur.execute("SELECT DISTINCT bowling_style FROM dim_players;")
print("\nPlayer bowling styles in dim_players (sample):")
try:
    for r in cur.fetchall()[:10]:
        print(r)
except Exception as e:
    print(f"Error checking bowling_style: {e}")

conn.close()
