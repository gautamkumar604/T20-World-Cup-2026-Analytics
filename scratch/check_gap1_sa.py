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
    # Start transaction
    cur.execute('BEGIN;')

    # Add columns temporarily in transaction
    cur.execute('''
    ALTER TABLE dim_matches 
        ADD COLUMN IF NOT EXISTS is_dls_abandoned boolean, 
        ADD COLUMN IF NOT EXISTS dls_allocated_overs numeric, 
        ADD COLUMN IF NOT EXISTS dls_abandonment_overs numeric, 
        ADD COLUMN IF NOT EXISTS dls_par_score integer;
    ''')

    # Deploy fn_calc_gcd in transaction
    with open('sql/analytics/view_tournament_standings_phase_4_9_6_15.sql', 'r') as f:
        sql_content = f.read()

    fn_sql = sql_content.split('CREATE OR REPLACE VIEW')[0]
    cur.execute(fn_sql)

    # Extract query part after 'AS' in CREATE VIEW
    view_sql = sql_content.split('CREATE OR REPLACE VIEW public.view_tournament_standings AS')[1].strip()

    # Run the 22-CTE query
    cur.execute(view_sql)
    rows = cur.fetchall()
    col_names = [d[0] for d in cur.description]
    print("Columns returned by view:", col_names)

    print("=== Super 8 Group 1 Standings from Live Data ===")
    s8_g1_teams = []
    for r in rows:
        row_dict = dict(zip(col_names, r))
        # Match Super 8 Group 1
        stage_val = row_dict.get('stage_normalized') or row_dict.get('stage')
        if stage_val == 'Super 8' and row_dict.get('group_name') == '1':
            s8_g1_teams.append(row_dict)
            print(f"Rank {row_dict['pool_rank']}: {row_dict['team_name']} | Pts: {row_dict['points']} | Played: {row_dict['played']} | Won: {row_dict['wins']} | Lost: {row_dict['losses']}")
            print(f"   Runs Scored: {row_dict['runs_scored']} / {row_dict['balls_faced']} balls")
            print(f"   Runs Conceded: {row_dict['runs_conceded']} / {row_dict['balls_bowled']} balls")
            print(f"   NRR Num/Den: {row_dict['nrr_num']} / {row_dict['nrr_den']}")
            print(f"   Canonical: {row_dict['nrr_canon_num']} / {row_dict['nrr_canon_den']}")
            print(f"   Decimal NRR: {row_dict['nrr_display']}")
            print("-" * 50)

finally:
    conn.rollback()
    print("Transaction rolled back cleanly.")
