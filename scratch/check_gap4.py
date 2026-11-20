import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432'),
    dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD')
)
cur = conn.cursor()

# Step 4A
cur.execute("""
SELECT EXISTS (
  SELECT 1 FROM pg_views
  WHERE schemaname='public' AND viewname='view_tournament_standings'
) AS view_exists;
""")
view_exists = cur.fetchone()[0]

# Step 4B
cur.execute("""
SELECT column_name FROM information_schema.columns
WHERE table_name='dim_matches'
  AND column_name IN ('dls_allocated_overs',
                      'dls_abandonment_overs',
                      'dls_par_score');
""")
dls_cols = cur.fetchall()

# Step 4C
cur.execute("""
SELECT EXISTS (
  SELECT 1 FROM pg_proc
  WHERE proname='fn_calc_gcd' AND pronamespace='public'::regnamespace
) AS fn_exists;
""")
fn_exists = cur.fetchone()[0]

print("=== GAP 4 Production Deployment Status ===")
print("Step 4A - view_tournament_standings exists:", view_exists)
print(f"Step 4B - DLS columns in dim_matches ({len(dls_cols)} rows):", [c[0] for c in dls_cols])
print("Step 4C - fn_calc_gcd exists:", fn_exists)
