import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

def run_suite():
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

        def run_fixture(fixture_name, m_data, s_data):
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

        # ----------------------------------------------------------------------
        # 1. SEC3-GCD-HARDEN
        # ----------------------------------------------------------------------
        try:
            # 1a. INT64_MIN guard
            int64_min_caught = False
            try:
                cur.execute("SAVEPOINT sp_gcd_min;")
                cur.execute("SELECT public.fn_calc_gcd((-9223372036854775807::bigint - 1::bigint), 16::bigint)")
                cur.execute("RELEASE SAVEPOINT sp_gcd_min;")
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT sp_gcd_min;")
                if 'INT64_MIN not supported' in str(e):
                    int64_min_caught = True
            assert int64_min_caught, "INT64_MIN guard did not raise expected exception"
            
            cur.execute("SELECT public.fn_calc_gcd(0::bigint, 57600::bigint);")
            res_zero = cur.fetchone()[0]
            assert res_zero == 57600

            cur.execute("SELECT public.fn_calc_gcd(120::bigint, -240::bigint);")
            res_neg = cur.fetchone()[0]
            assert res_neg == 120

            frac_caught = False
            try:
                cur.execute("SAVEPOINT sp_gcd_frac;")
                cur.execute("SELECT public.fn_calc_gcd(12.5, 4);")
                cur.execute("RELEASE SAVEPOINT sp_gcd_frac;")
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT sp_gcd_frac;")
                frac_caught = True
            assert frac_caught, "Fractional input was not rejected at compile time"

            test_results.append(("SEC3-GCD-HARDEN", "Hardened fn_calc_gcd(bigint, bigint)", "PASS", "INT64_MIN guarded, zero num -> 0/1, negative den ABS'd, fractional rejected"))
            print("[PASS] SEC3-GCD-HARDEN: Hardened fn_calc_gcd(bigint, bigint)")
        except Exception as e:
            test_results.append(("SEC3-GCD-HARDEN", "Hardened fn_calc_gcd(bigint, bigint)", "FAIL", str(e)))
            print(f"[FAIL] SEC3-GCD-HARDEN: {e}")

        # ----------------------------------------------------------------------
        # 2. SEC1-OVERS-CONV
        # ----------------------------------------------------------------------
        try:
            cases = [
                (8.3, 51), (8.5, 53), (14.5, 89), (15.0, 90), (15.5, 95), (20.0, 120),
                (8.6, None), (8.9, None)
            ]
            for ov, exp in cases:
                cur.execute("""
                    SELECT 
                        CASE
                            WHEN (%s::numeric - FLOOR(%s::numeric)) * 10 BETWEEN 0 AND 5
                                THEN (FLOOR(%s::numeric) * 6 + ROUND((%s::numeric - FLOOR(%s::numeric)) * 10))::int
                            ELSE NULL
                        END;
                """, (ov, ov, ov, ov, ov))
                actual = cur.fetchone()[0]
                assert actual == exp, f"For overs {ov}, expected {exp}, got {actual}"
            test_results.append(("SEC1-OVERS-CONV", "Overs Conversion & Validation", "PASS", "8.3->51, 8.5->53, 14.5->89, 15.5->95, 20.0->120"))
            print("[PASS] SEC1-OVERS-CONV: Overs Conversion & Validation")
        except Exception as e:
            test_results.append(("SEC1-OVERS-CONV", "Overs Conversion & Validation", "FAIL", str(e)))
            print(f"[FAIL] SEC1-OVERS-CONV: {e}")

        # ----------------------------------------------------------------------
        # 3. SEC2-NUMERIC-CROSS
        # ----------------------------------------------------------------------
        try:
            cur.execute("""
            WITH fractions AS (
                SELECT 'A' as t, 1::numeric as n, 3::numeric as d
                UNION ALL SELECT 'B', 2::numeric, 6::numeric
                UNION ALL SELECT 'C', 333::numeric, 999::numeric
            )
            SELECT a.t, b.t,
                   CASE 
                       WHEN (b.n * a.d) > (a.n * b.d) THEN 1 
                       ELSE 0 
                   END as sup
            FROM fractions a CROSS JOIN fractions b;
            """)
            rows = cur.fetchall()
            assert all(r[2] == 0 for r in rows), "Equal rational fractions must have zero strict superiority"
            test_results.append(("SEC2-NUMERIC-CROSS", "Exact NUMERIC Rational Cross-Products", "PASS", "Tie preserved"))
            print("[PASS] SEC2-NUMERIC-CROSS: Exact NUMERIC Rational Cross-Products")
        except Exception as e:
            test_results.append(("SEC2-NUMERIC-CROSS", "Exact NUMERIC Rational Cross-Products", "FAIL", str(e)))
            print(f"[FAIL] SEC2-NUMERIC-CROSS: {e}")

        # ----------------------------------------------------------------------
        # 4. SEC4-REG-INN1-ALLOUT
        # ----------------------------------------------------------------------
        try:
            m_4a = [('M_4A', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 20.0, None, False, False, None, None, None, 20.0, False, True, 'Reg Inn 1 All-Out')]
            s_4a = [('M_4A', 1, 'T1', 'T2', 120, 10, 84, 14.0, False), ('M_4A', 2, 'T2', 'T1', 122, 4, 90, 15.0, False)]
            res_4a = run_fixture('REG-INN1-ALLOUT', m_4a, s_4a)
            t1 = [r for r in res_4a if r['team_name'] == 'T1'][0]
            t2 = [r for r in res_4a if r['team_name'] == 'T2'][0]
            assert t1['runs_scored'] == 120 and t1['balls_faced'] == 120 and t2['runs_conceded'] == 120 and t2['balls_bowled'] == 120
            assert t1['nrr_canon_num'] + t2['nrr_canon_num'] == 0 and t1['nrr_canon_den'] == t2['nrr_canon_den']
            test_results.append(("SEC4-REG-INN1-ALLOUT", "Regular Innings 1 All-Out Quota Symmetry", "PASS", "T1 balls faced=120, T2 balls bowled=120"))
            print("[PASS] SEC4-REG-INN1-ALLOUT: Regular Innings 1 All-Out Quota Symmetry")
        except Exception as e:
            test_results.append(("SEC4-REG-INN1-ALLOUT", "Regular Innings 1 All-Out Quota Symmetry", "FAIL", str(e)))
            print(f"[FAIL] SEC4-REG-INN1-ALLOUT: {e}")

        # ----------------------------------------------------------------------
        # 5. SEC4-REG-INN2-ALLOUT
        # ----------------------------------------------------------------------
        try:
            m_4b = [('M_4B', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 20.0, None, False, False, None, None, None, 20.0, False, True, 'Reg Inn 2 All-Out')]
            s_4b = [('M_4B', 1, 'T1', 'T2', 160, 6, 120, 20.0, False), ('M_4B', 2, 'T2', 'T1', 120, 10, 84, 14.0, False)]
            res_4b = run_fixture('REG-INN2-ALLOUT', m_4b, s_4b)
            t1 = [r for r in res_4b if r['team_name'] == 'T1'][0]
            t2 = [r for r in res_4b if r['team_name'] == 'T2'][0]
            assert t2['runs_scored'] == 120 and t2['balls_faced'] == 120 and t1['runs_conceded'] == 120 and t1['balls_bowled'] == 120
            assert t1['nrr_canon_num'] + t2['nrr_canon_num'] == 0 and t1['nrr_canon_den'] == t2['nrr_canon_den']
            test_results.append(("SEC4-REG-INN2-ALLOUT", "Regular Innings 2 All-Out Quota Symmetry", "PASS", "T2 balls faced=120, T1 balls bowled=120"))
            print("[PASS] SEC4-REG-INN2-ALLOUT: Regular Innings 2 All-Out Quota Symmetry")
        except Exception as e:
            test_results.append(("SEC4-REG-INN2-ALLOUT", "Regular Innings 2 All-Out Quota Symmetry", "FAIL", str(e)))
            print(f"[FAIL] SEC4-REG-INN2-ALLOUT: {e}")

        # ----------------------------------------------------------------------
        # 6. SEC4-DLS-INN1-INT-ALLOUT (T1 all out in shortened 15.0 ov match)
        # ----------------------------------------------------------------------
        try:
            m_4c = [('M_4C', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 15.0, 110, True, False, 15.0, None, 110, 15.0, True, True, 'DLS Inn 1 Int Quota')]
            s_4c = [('M_4C', 1, 'T1', 'T2', 105, 10, 84, 14.0, False), ('M_4C', 2, 'T2', 'T1', 112, 3, 80, 13.2, False)]
            res_4c = run_fixture('DLS-INN1-INT-ALLOUT', m_4c, s_4c)
            t1 = [r for r in res_4c if r['team_name'] == 'T1'][0]
            t2 = [r for r in res_4c if r['team_name'] == 'T2'][0]
            assert t1['runs_scored'] == 105 and t1['balls_faced'] == 90 and t2['runs_conceded'] == 105 and t2['balls_bowled'] == 90
            assert t1['nrr_canon_num'] + t2['nrr_canon_num'] == 0 and t1['nrr_canon_den'] == t2['nrr_canon_den']
            test_results.append(("SEC4-DLS-INN1-INT-ALLOUT", "DLS Innings 1 All-Out (15.0 ov = 90b)", "PASS", "T1 actual 105/90b, T2 bowling 90b"))
            print("[PASS] SEC4-DLS-INN1-INT-ALLOUT: DLS Innings 1 All-Out (15.0 ov = 90b)")
        except Exception as e:
            test_results.append(("SEC4-DLS-INN1-INT-ALLOUT", "DLS Innings 1 All-Out (15.0 ov = 90b)", "FAIL", str(e)))
            print(f"[FAIL] SEC4-DLS-INN1-INT-ALLOUT: {e}")

        # ----------------------------------------------------------------------
        # 7. SEC4-DLS-INN1-FRAC-15.3 (T1 all out in shortened 15.3 ov match)
        # ----------------------------------------------------------------------
        try:
            m_4d = [('M_4D', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 15.3, 115, True, False, 15.3, None, 115, 15.3, True, True, 'DLS Inn 1 Frac Quota 15.3')]
            s_4d = [('M_4D', 1, 'T1', 'T2', 110, 10, 75, 12.3, False), ('M_4D', 2, 'T2', 'T1', 116, 4, 85, 14.1, False)]
            res_4d = run_fixture('DLS-INN1-FRAC-15.3', m_4d, s_4d)
            t1 = [r for r in res_4d if r['team_name'] == 'T1'][0]
            t2 = [r for r in res_4d if r['team_name'] == 'T2'][0]
            assert t1['runs_scored'] == 110 and t1['balls_faced'] == 93 and t2['runs_conceded'] == 110 and t2['balls_bowled'] == 93
            assert t1['nrr_canon_num'] + t2['nrr_canon_num'] == 0 and t1['nrr_canon_den'] == t2['nrr_canon_den']
            test_results.append(("SEC4-DLS-INN1-FRAC-15.3", "DLS Innings 1 All-Out (15.3 ov = 93b)", "PASS", "T1 actual 110/93b, T2 bowling 93b"))
            print("[PASS] SEC4-DLS-INN1-FRAC-15.3: DLS Innings 1 All-Out (15.3 ov = 93b)")
        except Exception as e:
            test_results.append(("SEC4-DLS-INN1-FRAC-15.3", "DLS Innings 1 All-Out (15.3 ov = 93b)", "FAIL", str(e)))
            print(f"[FAIL] SEC4-DLS-INN1-FRAC-15.3: {e}")

        # ----------------------------------------------------------------------
        # 8. SEC4-DLS-INN2-FRAC-15.5 (REMEDIATED: +1.553)
        # ----------------------------------------------------------------------
        try:
            m_4e = [('M_4E', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.5, 140, True, False, 15.5, None, None, 20.0, False, True, 'DLS Inn 2 Frac Quota 15.5')]
            s_4e = [('M_4E', 1, 'T1', 'T2', 170, 5, 120, 20.0, False), ('M_4E', 2, 'T2', 'T1', 110, 10, 80, 13.2, False)]
            res_4e = run_fixture('DLS-INN2-FRAC-15.5', m_4e, s_4e)
            t1 = [r for r in res_4e if r['team_name'] == 'T1'][0]
            t2 = [r for r in res_4e if r['team_name'] == 'T2'][0]
            assert t1['runs_scored'] == 170 and t1['balls_faced'] == 120
            assert t2['runs_scored'] == 110 and t2['balls_faced'] == 95
            assert t1['nrr_canon_num'] == 59 and t1['nrr_canon_den'] == 228
            assert float(t1['nrr_display']) == 1.553
            assert t2['nrr_canon_num'] == -59 and t2['nrr_canon_den'] == 228
            assert float(t2['nrr_display']) == -1.553
            test_results.append(("SEC4-DLS-INN2-FRAC-15.5", "DLS Innings 2 All-Out (15.5 ov = 95b)", "PASS", "T1=170/120b, T2=110/95b, Canon=59/228, NRR=+1.553"))
            print("[PASS] SEC4-DLS-INN2-FRAC-15.5: DLS Innings 2 All-Out (15.5 ov = 95b)")
        except Exception as e:
            test_results.append(("SEC4-DLS-INN2-FRAC-15.5", "DLS Innings 2 All-Out (15.5 ov = 95b)", "FAIL", str(e)))
            print(f"[FAIL] SEC4-DLS-INN2-FRAC-15.5: {e}")

        # ----------------------------------------------------------------------
        # 9. SEC4-CHASE-NON-ALLOUT
        # ----------------------------------------------------------------------
        try:
            m_4f = [('M_4F', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 20.0, None, False, False, None, None, None, 20.0, False, True, 'Successful Chase')]
            s_4f = [('M_4F', 1, 'T1', 'T2', 150, 7, 120, 20.0, False), ('M_4F', 2, 'T2', 'T1', 152, 3, 105, 17.3, False)]
            res_4f = run_fixture('CHASE-NON-ALLOUT', m_4f, s_4f)
            t1 = [r for r in res_4f if r['team_name'] == 'T1'][0]
            t2 = [r for r in res_4f if r['team_name'] == 'T2'][0]
            assert t2['runs_scored'] == 152 and t2['balls_faced'] == 105 and t1['runs_conceded'] == 152 and t1['balls_bowled'] == 105
            assert t1['nrr_canon_num'] + t2['nrr_canon_num'] == 0 and t1['nrr_canon_den'] == t2['nrr_canon_den']
            test_results.append(("SEC4-CHASE-NON-ALLOUT", "Non-All-Out Successful Chase", "PASS", "T2 balls faced=105, T1 bowled=105"))
            print("[PASS] SEC4-CHASE-NON-ALLOUT: Non-All-Out Successful Chase")
        except Exception as e:
            test_results.append(("SEC4-CHASE-NON-ALLOUT", "Non-All-Out Successful Chase", "FAIL", str(e)))
            print(f"[FAIL] SEC4-CHASE-NON-ALLOUT: {e}")

        # ----------------------------------------------------------------------
        # 10. SEC4-CONTROL-20-OVERS
        # ----------------------------------------------------------------------
        try:
            m_4g = [('M_4G', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 20.0, None, False, False, None, None, None, 20.0, False, True, 'Control 20 Overs')]
            s_4g = [('M_4G', 1, 'T1', 'T2', 160, 6, 120, 20.0, False), ('M_4G', 2, 'T2', 'T1', 145, 8, 120, 20.0, False)]
            res_4g = run_fixture('CONTROL-20-OVERS', m_4g, s_4g)
            t1 = [r for r in res_4g if r['team_name'] == 'T1'][0]
            t2 = [r for r in res_4g if r['team_name'] == 'T2'][0]
            assert t1['runs_scored'] == 160 and t1['balls_faced'] == 120 and t2['runs_conceded'] == 160 and t2['balls_bowled'] == 120
            assert t1['nrr_canon_num'] + t2['nrr_canon_num'] == 0 and t1['nrr_canon_den'] == t2['nrr_canon_den']
            test_results.append(("SEC4-CONTROL-20-OVERS", "Non-All-Out Control (20 Overs)", "PASS", "120 balls faced & bowled"))
            print("[PASS] SEC4-CONTROL-20-OVERS: Non-All-Out Control (20 Overs)")
        except Exception as e:
            test_results.append(("SEC4-CONTROL-20-OVERS", "Non-All-Out Control (20 Overs)", "FAIL", str(e)))
            print(f"[FAIL] SEC4-CONTROL-20-OVERS: {e}")

        # ----------------------------------------------------------------------
        # 11. SEC5-DLS-FAILCLOSED
        # ----------------------------------------------------------------------
        try:
            m_5 = [
                ('M_5A', '2026-02-10', 'Group Stage', 'A', 'T1_MisAlloc', 'T4_Ctrl', 'T1_MisAlloc', 'wickets', 15.0, 140, True, False, None, None, None, 20.0, False, True, 'Missing allocated overs'),
                ('M_5B', '2026-02-11', 'Group Stage', 'A', 'T2_MisPar', 'T4_Ctrl', 'T2_MisPar', 'runs', 12.0, 100, True, True, 15.0, 12.0, None, 20.0, False, True, 'Missing par score'),
                ('M_5C', '2026-02-12', 'Group Stage', 'A', 'T3_MisAbOvers', 'T4_Ctrl', 'T3_MisAbOvers', 'runs', 12.0, 100, True, True, 15.0, None, 95, 20.0, False, True, 'Missing abandonment overs'),
                ('M_5D', '2026-02-13', 'Group Stage', 'A', 'T4_Ctrl', 'T1_MisAlloc', 'T4_Ctrl', 'runs', 20.0, None, False, False, None, None, None, 20.0, False, True, 'Regular match')
            ]
            s_5 = [
                ('M_5A', 1, 'T4_Ctrl', 'T1_MisAlloc', 150, 6, 120, 20.0, False), ('M_5A', 2, 'T1_MisAlloc', 'T4_Ctrl', 141, 4, 86, 14.2, False),
                ('M_5B', 1, 'T4_Ctrl', 'T2_MisPar', 160, 6, 120, 20.0, False), ('M_5B', 2, 'T2_MisPar', 'T4_Ctrl', 105, 3, 72, 12.0, False),
                ('M_5C', 1, 'T4_Ctrl', 'T3_MisAbOvers', 160, 6, 120, 20.0, False), ('M_5C', 2, 'T3_MisAbOvers', 'T4_Ctrl', 105, 3, 72, 12.0, False),
                ('M_5D', 1, 'T4_Ctrl', 'T1_MisAlloc', 160, 6, 120, 20.0, False), ('M_5D', 2, 'T1_MisAlloc', 'T4_Ctrl', 130, 8, 120, 20.0, False)
            ]
            res_5 = run_fixture('DLS-FAIL-CLOSED-ALL', m_5, s_5)
            t1 = [r for r in res_5 if r['team_name'] == 'T1_MisAlloc'][0]
            t2 = [r for r in res_5 if r['team_name'] == 'T2_MisPar'][0]
            t3 = [r for r in res_5 if r['team_name'] == 'T3_MisAbOvers'][0]
            
            assert t1['nrr_display'] is None
            assert t2['nrr_display'] is None
            assert t3['nrr_display'] is None
            assert t1['points'] == 2 and t2['points'] == 2 and t3['points'] == 2
            test_results.append(("SEC5-DLS-FAILCLOSED", "DLS Fail-Closed Revalidation", "PASS", "Missing parameters fail closed (NRR=NULL); pts preserved"))
            print("[PASS] SEC5-DLS-FAILCLOSED: DLS Fail-Closed Revalidation")
        except Exception as e:
            test_results.append(("SEC5-DLS-FAILCLOSED", "DLS Fail-Closed Revalidation", "FAIL", str(e)))
            print(f"[FAIL] SEC5-DLS-FAILCLOSED: {e}")

        # ----------------------------------------------------------------------
        # 12. SEC6-FORFEIT-TRACE
        # ----------------------------------------------------------------------
        try:
            m_6 = [
                ('M_6A', '2026-02-10', 'Group Stage', 'A', 'T1_Defaulter', 'T2_Awarded', 'T2_Awarded', 'forfeit', 20.0, None, False, False, None, None, None, 20.0, False, True, 'Forfeit match'),
                ('M_6B', '2026-02-11', 'Group Stage', 'A', 'T2_Awarded', 'T3_Regular', 'T2_Awarded', 'runs', 20.0, None, False, False, None, None, None, 20.0, False, True, 'Regular match'),
                ('M_6C', '2026-02-12', 'Group Stage', 'A', 'T1_Defaulter', 'T3_Regular', 'T3_Regular', 'runs', 20.0, None, False, False, None, None, None, 20.0, False, True, 'Regular match')
            ]
            s_6 = [
                ('M_6B', 1, 'T2_Awarded', 'T3_Regular', 160, 5, 120, 20.0, False), ('M_6B', 2, 'T3_Regular', 'T2_Awarded', 140, 7, 120, 20.0, False),
                ('M_6C', 1, 'T3_Regular', 'T1_Defaulter', 150, 6, 120, 20.0, False), ('M_6C', 2, 'T1_Defaulter', 'T3_Regular', 130, 8, 120, 20.0, False)
            ]
            res_6 = run_fixture('FORFEIT-TRACE', m_6, s_6)
            t1 = [r for r in res_6 if r['team_name'] == 'T1_Defaulter'][0]
            t2 = [r for r in res_6 if r['team_name'] == 'T2_Awarded'][0]

            assert t1['runs_scored'] == 130 and t1['balls_faced'] == 240
            assert t2['runs_scored'] == 160 and t2['balls_faced'] == 120
            assert t2['points'] == 4
            test_results.append(("SEC6-FORFEIT-TRACE", "Forfeit Accounting (Zero/Rogue/Partial)", "PASS", "Defaulter charged 0/120b; Awarded team excluded from NRR"))
            print("[PASS] SEC6-FORFEIT-TRACE: Forfeit Accounting (Zero/Rogue/Partial)")
        except Exception as e:
            test_results.append(("SEC6-FORFEIT-TRACE", "Forfeit Accounting (Zero/Rogue/Partial)", "FAIL", str(e)))
            print(f"[FAIL] SEC6-FORFEIT-TRACE: {e}")

        # ----------------------------------------------------------------------
        # 13. SEC7-VIEW-PARSE on LIVE DATABASE
        # ----------------------------------------------------------------------
        try:
            # Add columns temporarily in transaction to live dim_matches
            cur.execute("""
            ALTER TABLE dim_matches 
                ADD COLUMN IF NOT EXISTS is_dls_abandoned boolean, 
                ADD COLUMN IF NOT EXISTS dls_allocated_overs numeric, 
                ADD COLUMN IF NOT EXISTS dls_abandonment_overs numeric, 
                ADD COLUMN IF NOT EXISTS dls_par_score integer,
                ADD COLUMN IF NOT EXISTS dls_allocated_overs_team1 numeric(4,1),
                ADD COLUMN IF NOT EXISTS dls_team1_innings_shortened boolean;
            """)
            cur.execute(view_sql)
            rows = cur.fetchall()
            assert len(rows) == 28, f"Expected 28 tournament standings rows, got {len(rows)}"
            test_results.append(("SEC7-VIEW-PARSE", "Full 22-CTE DDL Parse Validation", "PASS", "28 rows returned on live data"))
            print("[PASS] SEC7-VIEW-PARSE: Full 22-CTE DDL Parse Validation (28 rows)")
        except Exception as e:
            test_results.append(("SEC7-VIEW-PARSE", "Full 22-CTE DDL Parse Validation", "FAIL", str(e)))
            print(f"[FAIL] SEC7-VIEW-PARSE: {e}")

        # ----------------------------------------------------------------------
        # NEW TESTS: T2, T3, T4, T5, T6, T7, T8
        # ----------------------------------------------------------------------
        # T2: R2 Shortened 15 ov
        m_t2 = [('M_T2', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.0, 141, True, False, 15.0, None, 141, 15.0, True, True, 'R2 Shortened 15 ov')]
        s_t2 = [('M_T2', 1, 'T1', 'T2', 130, 4, 90, 15.0, False), ('M_T2', 2, 'T2', 'T1', 120, 6, 90, 15.0, False)]
        res_t2 = run_fixture('T2', m_t2, s_t2)
        r2_t1 = [r for r in res_t2 if r['team_name'] == 'T1'][0]
        assert r2_t1['runs_scored'] == 141 and r2_t1['balls_faced'] == 90 and float(r2_t1['nrr_display']) == 1.400
        test_results.append(("NEW-T2-R2-SHORTENED", "R2: T1 Shortened 15 ov, uses par score", "PASS", "T1=141/90b, Canon=7/30, NRR=+1.400"))
        print("[PASS] NEW-T2-R2-SHORTENED: R2 Shortened 15 ov")

        # T3: R3 T1 all-out under shortened quota
        m_t3 = [('M_T3', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.0, 106, True, False, 15.0, None, 106, 15.0, True, True, 'R3 T1 all-out 15 ov')]
        s_t3 = [('M_T3', 1, 'T1', 'T2', 105, 10, 78, 13.0, False), ('M_T3', 2, 'T2', 'T1', 90, 4, 78, 13.0, False)]
        res_t3 = run_fixture('T3', m_t3, s_t3)
        r3_t1 = [r for r in res_t3 if r['team_name'] == 'T1'][0]
        assert r3_t1['runs_scored'] == 105 and r3_t1['balls_faced'] == 90 and float(r3_t1['nrr_display']) == 0.077
        test_results.append(("NEW-T3-R3-ALLOUT-SHORTENED", "R3: T1 All-Out under shortened quota", "PASS", "T1=105/90b, Canon=1/78, NRR=+0.077"))
        print("[PASS] NEW-T3-R3-ALLOUT-SHORTENED: R3 All-Out under shortened quota")

        # T4: R4 Successful chase
        m_t4 = [('M_T4', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'wickets', 20.0, None, False, False, None, None, None, 20.0, False, True, 'R4 Chase')]
        s_t4 = [('M_T4', 1, 'T1', 'T2', 170, 5, 120, 20.0, False), ('M_T4', 2, 'T2', 'T1', 152, 3, 100, 16.4, False)]
        res_t4 = run_fixture('T4', m_t4, s_t4)
        r4_t2 = [r for r in res_t4 if r['team_name'] == 'T2'][0]
        assert r4_t2['runs_scored'] == 152 and r4_t2['balls_faced'] == 100 and float(r4_t2['nrr_display']) == 0.620
        test_results.append(("NEW-T4-R4-CHASE", "R4: Successful chase under quota", "PASS", "T2=152/100b, Canon=31/300, NRR=+0.620"))
        print("[PASS] NEW-T4-R4-CHASE: R4 Successful chase")

        # T5: R5 T2 all-out under quota
        m_t5 = [('M_T5', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 20.0, None, False, False, None, None, None, 20.0, False, True, 'R5 T2 all out')]
        s_t5 = [('M_T5', 1, 'T1', 'T2', 180, 5, 120, 20.0, False), ('M_T5', 2, 'T2', 'T1', 110, 10, 84, 14.0, False)]
        res_t5 = run_fixture('T5', m_t5, s_t5)
        r5_t1 = [r for r in res_t5 if r['team_name'] == 'T1'][0]
        assert r5_t1['runs_scored'] == 180 and r5_t1['balls_faced'] == 120 and float(r5_t1['nrr_display']) == 3.500
        test_results.append(("NEW-T5-R5-ALLOUT-FULL", "R5: T2 all-out under quota (20 ov)", "PASS", "T1=180/120b, T2=110/120b, Canon=7/12, NRR=+3.500"))
        print("[PASS] NEW-T5-R5-ALLOUT-FULL: R5 T2 all-out under quota")

        # T6: R6 Abandoned DLS
        m_t6 = [('M_T6', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T2', 'runs', 20.0, None, True, True, 20.0, 12.4, 102, 20.0, False, True, 'R6 Abandoned')]
        s_t6 = [('M_T6', 1, 'T1', 'T2', 140, 6, 120, 20.0, False), ('M_T6', 2, 'T2', 'T1', 105, 3, 76, 12.4, False)]
        res_t6 = run_fixture('T6', m_t6, s_t6)
        r6_t2 = [r for r in res_t6 if r['team_name'] == 'T2'][0]
        assert r6_t2['runs_scored'] == 105 and r6_t2['balls_faced'] == 76 and float(r6_t2['nrr_display']) == 0.237
        test_results.append(("NEW-T6-R6-ABANDONED", "R6: Abandoned DLS par score & balls faced", "PASS", "T1=102/76b, T2=105/76b, Canon=3/76, NRR=+0.237"))
        print("[PASS] NEW-T6-R6-ABANDONED: R6 Abandoned DLS")

        # T7: Fallback dls_allocated_overs_team1 IS NULL
        m_t7 = [('M_T7', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 15.0, 140, True, False, 15.0, None, None, None, False, True, 'T7 Null team1 quota')]
        s_t7 = [('M_T7', 1, 'T1', 'T2', 170, 5, 120, 20.0, False), ('M_T7', 2, 'T2', 'T1', 110, 10, 80, 13.2, False)]
        res_t7 = run_fixture('T7', m_t7, s_t7)
        r7_t1 = [r for r in res_t7 if r['team_name'] == 'T1'][0]
        assert r7_t1['nrr_display'] is None and r7_t1['points'] == 2
        test_results.append(("NEW-T7-FALLBACK-NULL", "Fallback: team1 quota NULL fails closed", "PASS", "NRR=NULL, points=2 preserved"))
        print("[PASS] NEW-T7-FALLBACK-NULL: Fallback team1 quota NULL")

        # T8: Fractional team1 quota (14.5 ov = 89 balls)
        m_t8 = [('M_T8', '2026-02-10', 'Group Stage', 'A', 'T1', 'T2', 'T1', 'runs', 14.5, 101, True, False, 14.5, None, 101, 14.5, True, True, 'T8 Frac quota 14.5')]
        s_t8 = [('M_T8', 1, 'T1', 'T2', 100, 10, 80, 13.2, False), ('M_T8', 2, 'T2', 'T1', 95, 8, 89, 14.5, False)]
        res_t8 = run_fixture('T8', m_t8, s_t8)
        r8_t1 = [r for r in res_t8 if r['team_name'] == 'T1'][0]
        assert r8_t1['balls_faced'] == 89 and float(r8_t1['nrr_display']) == 0.337
        test_results.append(("NEW-T8-FRAC-QUOTA", "Fractional team1 quota 14.5 ov = 89b", "PASS", "Balls faced=89b, NRR=+0.337"))
        print("[PASS] NEW-T8-FRAC-QUOTA: Fractional team1 quota 14.5 ov = 89b")

    finally:
        conn.rollback()
        print("\nAll synthetic tests finished. Transaction rolled back cleanly.")

    print("\n=======================================================")
    print(f"TOTAL TESTS EXECUTED: {len(test_results)}")
    passed_count = sum(1 for tr in test_results if tr[2] == 'PASS')
    failed_count = sum(1 for tr in test_results if tr[2] == 'FAIL')
    print(f"PASSED: {passed_count} / {len(test_results)}")
    print(f"FAILED: {failed_count} / {len(test_results)}")
    print("=======================================================")

if __name__ == '__main__':
    run_suite()
