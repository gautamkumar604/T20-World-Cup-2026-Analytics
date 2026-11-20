import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

def run_tests():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )
    cur = conn.cursor()

    test_results = []

    try:
        cur.execute("BEGIN;")

        # Read phase 16 SQL
        with open('sql/analytics/view_tournament_standings_phase_4_9_6_16.sql', 'r') as f:
            sql_content = f.read()

        fn_sql = sql_content.split('CREATE OR REPLACE VIEW')[0]
        cur.execute(fn_sql)

        view_sql = sql_content.split('CREATE OR REPLACE VIEW public.view_tournament_standings AS')[1].strip()

        # Temporary tables with schema extensions
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
            dls_allocated_overs_team1 numeric(4,1),
            dls_team1_innings_shortened boolean,
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

        harness_sql = view_sql.replace('FROM dim_matches', 'FROM temp_dim_matches').replace('FROM fact_match_summaries', 'FROM temp_fact_match_summaries')

        def run_fixture(m_data, s_data):
            cur.execute("TRUNCATE temp_dim_matches, temp_fact_match_summaries;")
            for m in m_data:
                cur.execute("""
                INSERT INTO temp_dim_matches VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, m)
            for s in s_data:
                cur.execute("""
                INSERT INTO temp_fact_match_summaries VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, s)
            cur.execute(harness_sql)
            col_names = [d[0] for d in cur.description]
            return [dict(zip(col_names, row)) for row in cur.fetchall()]

        print("=== EXECUTING TASK 4 TESTS (T1 - T8) ===")

        # ----------------------------------------------------------------------
        # TEST T1: Rule R1 — Team 1 batted full 20 ov, Team 2 all-out under quota
        # ----------------------------------------------------------------------
        m_t1 = [('M_T1', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.5, 140, True, False, 15.5, None, None, 20.0, False, True, 'R1 Full 20 ov')]
        s_t1 = [('M_T1', 1, 'T1', 'T2', 170, 5, 120, 20.0, False), ('M_T1', 2, 'T2', 'T1', 110, 10, 80, 13.2, False)]
        res_t1 = run_fixture(m_t1, s_t1)
        r_t1 = [r for r in res_t1 if r['team_name'] == 'T1'][0]
        r_t2 = [r for r in res_t1 if r['team_name'] == 'T2'][0]
        
        print("T1 Result:")
        print(f"  T1: Runs Scored={r_t1['runs_scored']}, Balls Faced={r_t1['balls_faced']}, Runs Conceded={r_t1['runs_conceded']}, Balls Bowled={r_t1['balls_bowled']}")
        print(f"  T1: Num={r_t1['nrr_num']}, Den={r_t1['nrr_den']}, Canonical={r_t1['nrr_canon_num']}/{r_t1['nrr_canon_den']}, NRR={r_t1['nrr_display']}")
        print(f"  T2: Canonical={r_t2['nrr_canon_num']}/{r_t2['nrr_canon_den']}, NRR={r_t2['nrr_display']}")

        assert r_t1['runs_scored'] == 170 and r_t1['balls_faced'] == 120, f"Expected 170/120b, got {r_t1['runs_scored']}/{r_t1['balls_faced']}"
        assert r_t2['runs_scored'] == 110 and r_t2['balls_faced'] == 95, f"Expected 110/95b, got {r_t2['runs_scored']}/{r_t2['balls_faced']}"
        assert r_t1['nrr_canon_num'] == 59 and r_t1['nrr_canon_den'] == 228, f"Expected 59/228, got {r_t1['nrr_canon_num']}/{r_t1['nrr_canon_den']}"
        assert float(r_t1['nrr_display']) == 1.553, f"Expected +1.553, got {r_t1['nrr_display']}"
        assert r_t2['nrr_canon_num'] == -59 and r_t2['nrr_canon_den'] == 228
        assert float(r_t2['nrr_display']) == -1.553
        test_results.append(("T1-R1-FULL-20-DLS-INN2", "R1: T1 Full 20 ov, T2 all-out under quota", "PASS", f"T1=170/120b, T2=110/95b, Canon=59/228, NRR=+1.553"))
        print("[PASS] T1: R1 — Team 1 batted full 20 ov, Team 2 all-out under quota")

        # ----------------------------------------------------------------------
        # TEST T2: Rule R2 — Team 1 innings shortened to 15 ov by rain
        # ----------------------------------------------------------------------
        m_t2 = [('M_T2', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.0, 141, True, False, 15.0, None, 141, 15.0, True, True, 'R2 Shortened 15 ov')]
        s_t2 = [('M_T2', 1, 'T1', 'T2', 130, 4, 90, 15.0, False), ('M_T2', 2, 'T2', 'T1', 120, 6, 90, 15.0, False)]
        res_t2 = run_fixture(m_t2, s_t2)
        r2_t1 = [r for r in res_t2 if r['team_name'] == 'T1'][0]
        r2_t2 = [r for r in res_t2 if r['team_name'] == 'T2'][0]

        print("T2 Result:")
        print(f"  T1: Runs Scored={r2_t1['runs_scored']}, Balls Faced={r2_t1['balls_faced']}, Runs Conceded={r2_t1['runs_conceded']}, Balls Bowled={r2_t1['balls_bowled']}")
        print(f"  T1: Num={r2_t1['nrr_num']}, Den={r2_t1['nrr_den']}, Canonical={r2_t1['nrr_canon_num']}/{r2_t1['nrr_canon_den']}, NRR={r2_t1['nrr_display']}")

        assert r2_t1['runs_scored'] == 141 and r2_t1['balls_faced'] == 90
        assert r2_t2['runs_scored'] == 120 and r2_t2['balls_faced'] == 90
        assert r2_t1['nrr_canon_num'] == 7 and r2_t1['nrr_canon_den'] == 30
        assert float(r2_t1['nrr_display']) == 1.400
        test_results.append(("T2-R2-SHORTENED-15OV", "R2: T1 Shortened 15 ov, uses par score", "PASS", f"T1=141/90b, T2=120/90b, Canon=7/30, NRR=+1.400"))
        print("[PASS] T2: R2 — Team 1 innings shortened to 15 ov by rain")

        # ----------------------------------------------------------------------
        # TEST T3: Rule R3 — Team 1 all-out under shortened allocation
        # ----------------------------------------------------------------------
        m_t3 = [('M_T3', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.0, 106, True, False, 15.0, None, 106, 15.0, True, True, 'R3 T1 all-out 15 ov')]
        s_t3 = [('M_T3', 1, 'T1', 'T2', 105, 10, 78, 13.0, False), ('M_T3', 2, 'T2', 'T1', 90, 4, 78, 13.0, False)]
        res_t3 = run_fixture(m_t3, s_t3)
        r3_t1 = [r for r in res_t3 if r['team_name'] == 'T1'][0]
        r3_t2 = [r for r in res_t3 if r['team_name'] == 'T2'][0]

        print("T3 Result:")
        print(f"  T1: Runs Scored={r3_t1['runs_scored']}, Balls Faced={r3_t1['balls_faced']}, Runs Conceded={r3_t1['runs_conceded']}, Balls Bowled={r3_t1['balls_bowled']}")
        print(f"  T1: Num={r3_t1['nrr_num']}, Den={r3_t1['nrr_den']}, Canonical={r3_t1['nrr_canon_num']}/{r3_t1['nrr_canon_den']}, NRR={r3_t1['nrr_display']}")

        assert r3_t1['runs_scored'] == 105 and r3_t1['balls_faced'] == 90
        assert r3_t2['runs_scored'] == 90 and r3_t2['balls_faced'] == 78
        assert r3_t1['nrr_canon_num'] == 1 and r3_t1['nrr_canon_den'] == 78
        assert float(r3_t1['nrr_display']) == 0.077
        test_results.append(("T3-R3-T1-ALLOUT-SHORTENED", "R3: T1 All-Out under shortened quota", "PASS", f"T1=105/90b, T2=90/78b, Canon=1/78, NRR=+0.077"))
        print("[PASS] T3: R3 — Team 1 all-out under shortened allocation")

        # ----------------------------------------------------------------------
        # TEST T4: Rule R4 — Team 2 successful chase (regular completed)
        # ----------------------------------------------------------------------
        m_t4 = [('M_T4', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 20.0, None, False, False, None, None, None, 20.0, False, True, 'R4 Chase')]
        s_t4 = [('M_T4', 1, 'T1', 'T2', 170, 5, 120, 20.0, False), ('M_T4', 2, 'T2', 'T1', 152, 3, 100, 16.4, False)]
        res_t4 = run_fixture(m_t4, s_t4)
        r4_t1 = [r for r in res_t4 if r['team_name'] == 'T1'][0]
        r4_t2 = [r for r in res_t4 if r['team_name'] == 'T2'][0]

        print("T4 Result:")
        print(f"  T2: Runs Scored={r4_t2['runs_scored']}, Balls Faced={r4_t2['balls_faced']}, Runs Conceded={r4_t2['runs_conceded']}, Balls Bowled={r4_t2['balls_bowled']}")
        print(f"  T2: Num={r4_t2['nrr_num']}, Den={r4_t2['nrr_den']}, Canonical={r4_t2['nrr_canon_num']}/{r4_t2['nrr_canon_den']}, NRR={r4_t2['nrr_display']}")

        assert r4_t1['runs_scored'] == 170 and r4_t1['balls_faced'] == 120
        assert r4_t2['runs_scored'] == 152 and r4_t2['balls_faced'] == 100
        assert r4_t2['nrr_canon_num'] == 31 and r4_t2['nrr_canon_den'] == 300
        assert float(r4_t2['nrr_display']) == 0.620
        test_results.append(("T4-R4-CHASE-SUCCESS", "R4: Team 2 successful chase under quota", "PASS", f"T1=170/120b, T2=152/100b, Canon=31/300, NRR=+0.620"))
        print("[PASS] T4: R4 — Team 2 successful chase (regular completed)")

        # ----------------------------------------------------------------------
        # TEST T5: Rule R5 — Team 2 all-out under quota (non-shortened match, 20 ov)
        # ----------------------------------------------------------------------
        m_t5 = [('M_T5', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 20.0, None, False, False, None, None, None, 20.0, False, True, 'R5 T2 all out')]
        s_t5 = [('M_T5', 1, 'T1', 'T2', 180, 5, 120, 20.0, False), ('M_T5', 2, 'T2', 'T1', 110, 10, 84, 14.0, False)]
        res_t5 = run_fixture(m_t5, s_t5)
        r5_t1 = [r for r in res_t5 if r['team_name'] == 'T1'][0]
        r5_t2 = [r for r in res_t5 if r['team_name'] == 'T2'][0]

        print("T5 Result:")
        print(f"  T1: Runs Scored={r5_t1['runs_scored']}, Balls Faced={r5_t1['balls_faced']}, Runs Conceded={r5_t1['runs_conceded']}, Balls Bowled={r5_t1['balls_bowled']}")
        print(f"  T1: Num={r5_t1['nrr_num']}, Den={r5_t1['nrr_den']}, Canonical={r5_t1['nrr_canon_num']}/{r5_t1['nrr_canon_den']}, NRR={r5_t1['nrr_display']}")

        assert r5_t1['runs_scored'] == 180 and r5_t1['balls_faced'] == 120
        assert r5_t2['runs_scored'] == 110 and r5_t2['balls_faced'] == 120
        assert r5_t1['nrr_canon_num'] == 7 and r5_t1['nrr_canon_den'] == 12
        assert float(r5_t1['nrr_display']) == 3.500
        test_results.append(("T5-R5-T2-ALLOUT-FULL", "R5: Team 2 all-out under quota (20 ov)", "PASS", f"T1=180/120b, T2=110/120b, Canon=7/12, NRR=+3.500"))
        print("[PASS] T5: R5 — Team 2 all-out under quota (non-shortened match, 20 ov)")

        # ----------------------------------------------------------------------
        # TEST T6: Rule R6 — Abandoned DLS (dls_status=2)
        # ----------------------------------------------------------------------
        m_t6 = [('M_T6', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'runs', 20.0, None, True, True, 20.0, 12.4, 102, 20.0, False, True, 'R6 Abandoned')]
        s_t6 = [('M_T6', 1, 'T1', 'T2', 140, 6, 120, 20.0, False), ('M_T6', 2, 'T2', 'T1', 105, 3, 76, 12.4, False)]
        res_t6 = run_fixture(m_t6, s_t6)
        r6_t1 = [r for r in res_t6 if r['team_name'] == 'T1'][0]
        r6_t2 = [r for r in res_t6 if r['team_name'] == 'T2'][0]

        print("T6 Result:")
        print(f"  T2: Runs Scored={r6_t2['runs_scored']}, Balls Faced={r6_t2['balls_faced']}, Runs Conceded={r6_t2['runs_conceded']}, Balls Bowled={r6_t2['balls_bowled']}")
        print(f"  T2: Num={r6_t2['nrr_num']}, Den={r6_t2['nrr_den']}, Canonical={r6_t2['nrr_canon_num']}/{r6_t2['nrr_canon_den']}, NRR={r6_t2['nrr_display']}")

        assert r6_t1['runs_scored'] == 102 and r6_t1['balls_faced'] == 76
        assert r6_t2['runs_scored'] == 105 and r6_t2['balls_faced'] == 76
        assert r6_t2['nrr_canon_num'] == 3 and r6_t2['nrr_canon_den'] == 76
        assert float(r6_t2['nrr_display']) == 0.237
        test_results.append(("T6-R6-ABANDONED-DLS", "R6: Abandoned DLS uses par score & balls faced", "PASS", f"T1=102/76b, T2=105/76b, Canon=3/76, NRR=+0.237"))
        print("[PASS] T6: R6 — Abandoned DLS (dls_status=2)")

        # ----------------------------------------------------------------------
        # TEST T7: Fallback — dls_allocated_overs_team1 IS NULL
        # ----------------------------------------------------------------------
        m_t7 = [('M_T7', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.0, 140, True, False, 15.0, None, None, None, False, True, 'T7 Null team1 quota')]
        s_t7 = [('M_T7', 1, 'T1', 'T2', 170, 5, 120, 20.0, False), ('M_T7', 2, 'T2', 'T1', 110, 10, 80, 13.2, False)]
        res_t7 = run_fixture(m_t7, s_t7)
        r7_t1 = [r for r in res_t7 if r['team_name'] == 'T1'][0]
        r7_t2 = [r for r in res_t7 if r['team_name'] == 'T2'][0]

        print("T7 Result:")
        print(f"  T1: NRR={r7_t1['nrr_display']}, Points={r7_t1['points']}, Step={r7_t1['resolution_step']}")

        assert r7_t1['nrr_display'] is None and r7_t2['nrr_display'] is None, "NRR must fail closed to NULL"
        assert r7_t1['points'] == 2 and r7_t2['points'] == 0, "Points must be preserved"
        test_results.append(("T7-FALLBACK-NULL-QUOTA", "Fallback: dls_allocated_overs_team1 IS NULL fails closed", "PASS", "NRR=NULL, points=2/0 preserved"))
        print("[PASS] T7: Fallback — dls_allocated_overs_team1 IS NULL")

        # ----------------------------------------------------------------------
        # TEST T8: Fractional team1 quota (14.5 ov = 89 balls)
        # ----------------------------------------------------------------------
        m_t8 = [('M_T8', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 14.5, 101, True, False, 14.5, None, 101, 14.5, True, True, 'T8 Frac team1 quota 14.5')]
        s_t8 = [('M_T8', 1, 'T1', 'T2', 100, 10, 80, 13.2, False), ('M_T8', 2, 'T2', 'T1', 95, 8, 89, 14.5, False)]
        res_t8 = run_fixture(m_t8, s_t8)
        r8_t1 = [r for r in res_t8 if r['team_name'] == 'T1'][0]
        r8_t2 = [r for r in res_t8 if r['team_name'] == 'T2'][0]

        print("T8 Result:")
        print(f"  T1: Runs Scored={r8_t1['runs_scored']}, Balls Faced={r8_t1['balls_faced']}, Runs Conceded={r8_t1['runs_conceded']}, Balls Bowled={r8_t1['balls_bowled']}")
        print(f"  T1: Num={r8_t1['nrr_num']}, Den={r8_t1['nrr_den']}, Canonical={r8_t1['nrr_canon_num']}/{r8_t1['nrr_canon_den']}, NRR={r8_t1['nrr_display']}")

        assert r8_t1['balls_faced'] == 89, f"Expected 89 balls (14.5 ov), got {r8_t1['balls_faced']}"
        assert r8_t2['balls_bowled'] == 89
        test_results.append(("T8-FRAC-TEAM1-QUOTA", "Fractional team1 quota (14.5 ov = 89b)", "PASS", "Balls faced=89b, all-out symmetry=89b"))
        print("[PASS] T8: Fractional team1 quota (14.5 ov = 89 balls)")

    finally:
        conn.rollback()
        print("\nAll synthetic tests finished. Transaction rolled back cleanly.")

    print("\n=== SUMMARY OF TESTS ===")
    for tr in test_results:
        print(f"[{tr[2]}] {tr[0]}: {tr[1]} -> {tr[3]}")

if __name__ == '__main__':
    run_tests()
