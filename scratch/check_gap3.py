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

try:
    cur.execute("BEGIN;")

    # Add columns temporarily in transaction
    cur.execute('''
    ALTER TABLE dim_matches 
        ADD COLUMN IF NOT EXISTS is_dls_abandoned boolean, 
        ADD COLUMN IF NOT EXISTS dls_allocated_overs numeric, 
        ADD COLUMN IF NOT EXISTS dls_abandonment_overs numeric, 
        ADD COLUMN IF NOT EXISTS dls_par_score integer;
    ''')

    with open('sql/analytics/view_tournament_standings_phase_4_9_6_15.sql', 'r') as f:
        sql_content = f.read()

    fn_sql = sql_content.split('CREATE OR REPLACE VIEW')[0]
    cur.execute(fn_sql)

    view_sql = sql_content.split('CREATE OR REPLACE VIEW public.view_tournament_standings AS')[1].strip()

    cur.execute(view_sql)
    col_names = [d[0] for d in cur.description]
    rows = cur.fetchall()

    all_rows = [dict(zip(col_names, r)) for r in rows]

    print("=== Super 8 Teams in Live Database (Step 3A) ===")
    s8_rows = [r for r in all_rows if r['stage_normalized'] == 'Super 8']
    s8_rows.sort(key=lambda x: (x['group_name'], -x['points'], -float(x['nrr_display']) if x['nrr_display'] else 0))
    for r in s8_rows:
        print(f"Group {r['group_name']} | Rank {r['pool_rank']}: {r['team_name']} | Pts: {r['points']} | Won: {r['wins']} | Lost: {r['losses']} | NRR: {r['nrr_display']}")

    print("\n=== Group Stage Standings & Top 2 Qualifiers (Step 3B) ===")
    gs_rows = [r for r in all_rows if r['stage_normalized'] == 'Group Stage']
    gs_rows.sort(key=lambda x: (x['group_name'], r['pool_rank']))
    for r in gs_rows:
        qual = "--> QUALIFIED FOR S8" if r['pool_rank'] in (1, 2) else ""
        print(f"Group {r['group_name']} | Rank {r['pool_rank']}: {r['team_name']} | Pts: {r['points']} | NRR: {r['nrr_display']} {qual}")

    print("\n=== Super 8 Group 1 Roster vs Group 2 Roster (Step 3C) ===")
    g1_teams = [r['team_name'] for r in s8_rows if r['group_name'] == '1']
    g2_teams = [r['team_name'] for r in s8_rows if r['group_name'] == '2']
    print("Super 8 Group 1:", g1_teams)
    print("Super 8 Group 2:", g2_teams)

finally:
    conn.rollback()
    print("\nTransaction rolled back cleanly.")
