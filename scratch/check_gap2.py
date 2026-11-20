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

    # Setup temp tables matching the test harness
    cur.execute("""
    CREATE TEMP TABLE temp_dim_matches (
        match_id varchar(50) PRIMARY KEY,
        match_date date,
        stage varchar(50),
        group_name varchar(10),
        team1 varchar(50),
        team2 varchar(50),
        winner varchar(50),
        outcome_type varchar(50),
        target_overs numeric,
        target_runs integer,
        is_dls_applied boolean,
        is_dls_abandoned boolean,
        dls_allocated_overs numeric,
        dls_abandonment_overs numeric,
        dls_par_score integer,
        scorecard_available boolean,
        source_note text
    );

    CREATE TEMP TABLE temp_fact_match_summaries (
        match_id varchar(50),
        innings integer,
        batting_team varchar(50),
        bowling_team varchar(50),
        total_runs integer,
        total_wickets integer,
        legal_deliveries integer,
        total_overs numeric,
        is_super_over boolean
    );
    """)

    # Insert fixture SEC4-DLS-INN2-FRAC-15.5
    m_4e = ('M_4E', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.5, 140, True, False, 15.5, None, None, True, 'DLS Inn 2 Frac Quota 15.5')
    s_4e = [
        ('M_4E', 1, 'T1', 'T2', 170, 5, 120, 20.0, False),
        ('M_4E', 2, 'T2', 'T1', 110, 10, 80, 13.2, False)
    ]

    cur.execute("""
    INSERT INTO temp_dim_matches VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, m_4e)

    for s in s_4e:
        cur.execute("""
        INSERT INTO temp_fact_match_summaries VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, s)

    # Deploy fn_calc_gcd in transaction
    with open('sql/analytics/view_tournament_standings_phase_4_9_6_15.sql', 'r') as f:
        sql_content = f.read()

    fn_sql = sql_content.split('CREATE OR REPLACE VIEW')[0]
    cur.execute(fn_sql)

    view_sql = sql_content.split('CREATE OR REPLACE VIEW public.view_tournament_standings AS')[1].strip()
    # Replace references to dim_matches and fact_match_summaries with temp tables
    harness_sql = view_sql.replace('FROM dim_matches', 'FROM temp_dim_matches').replace('FROM fact_match_summaries', 'FROM temp_fact_match_summaries')

    # Query match_played_eval to see dls_status directly
    cur.execute("""
    WITH stage_matches AS (
        SELECT 
            match_id, match_date, stage,
            CASE 
                WHEN group_name IN ('A', 'B', 'C', 'D') THEN 'Group Stage'
                WHEN group_name IN ('1', '2') THEN 'Super 8'
                ELSE COALESCE(stage, 'Knockout') 
            END AS stage_normalized,
            group_name, team1, team2, winner, outcome_type, target_overs, target_runs,
            is_dls_applied, is_dls_abandoned, dls_allocated_overs, dls_abandonment_overs,
            dls_par_score, scorecard_available, source_note
        FROM temp_dim_matches
    ),
    match_opponents AS (
        SELECT stage_normalized, group_name, match_id, team1 AS focus_team, team2 AS opp_team,
               winner, outcome_type, target_overs, target_runs, is_dls_applied, is_dls_abandoned,
               dls_allocated_overs, dls_abandonment_overs, dls_par_score, scorecard_available, source_note
        FROM stage_matches
    )
    SELECT focus_team, opp_team, outcome_type, target_runs, is_dls_applied, is_dls_abandoned,
           CASE 
               WHEN is_dls_applied = FALSE THEN 0
               WHEN outcome_type NOT IN ('runs', 'wickets', 'tie', 'tie_super_over') THEN 0
               WHEN is_dls_abandoned IS NULL THEN 5
               WHEN is_dls_abandoned = FALSE THEN
                   CASE 
                       WHEN target_runs IS NOT NULL AND dls_allocated_overs IS NOT NULL 
                            AND dls_allocated_overs > 0 
                            AND (dls_allocated_overs - FLOOR(dls_allocated_overs)) * 10 BETWEEN 0 AND 5 THEN 1
                       ELSE 3
                   END
               WHEN is_dls_abandoned = TRUE THEN
                   CASE 
                       WHEN dls_par_score IS NOT NULL AND dls_abandonment_overs IS NOT NULL 
                            AND dls_abandonment_overs > 0 
                            AND (dls_abandonment_overs - FLOOR(dls_abandonment_overs)) * 10 BETWEEN 0 AND 5 THEN 2
                       ELSE 4
                   END
               ELSE 5
           END AS dls_status
    FROM match_opponents;
    """)

    print("=== Step 2A Evaluation ===")
    for row in cur.fetchall():
        print("match_played_eval row:", row)

    # Now execute the harness SQL to see runs_scored and balls_faced for T1 and T2
    cur.execute(harness_sql)
    col_names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    for r in rows:
        d = dict(zip(col_names, r))
        print(f"Team: {d['team_name']} | Runs Scored: {d['runs_scored']} | Balls Faced: {d['balls_faced']} | Runs Conceded: {d['runs_conceded']} | Balls Bowled: {d['balls_bowled']} | NRR: {d['nrr_display']}")

finally:
    conn.rollback()
    print("Transaction rolled back cleanly.")
