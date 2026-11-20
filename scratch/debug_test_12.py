import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import psycopg2
from test_phase4_9_6_13_audit import build_20cte_query

conn = psycopg2.connect('dbname=t20_worldcup_2026 user=postgres password=Gautam@101 host=localhost port=5432')
cur = conn.cursor()
cur.execute('BEGIN;')

gcd_ddl = """
CREATE OR REPLACE FUNCTION gcd(a NUMERIC, b NUMERIC)
RETURNS NUMERIC AS $$
BEGIN
    RETURN 1;
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;
"""
cur.execute(gcd_ddl)

matches_sql = """
    SELECT 'M1' AS match_id, '2026-02-10'::date AS match_date, 'Group Stage' AS stage, 'Group Stage' AS stage_normalized, 'A' AS group_name, 'TeamA' AS team1, 'TeamB' AS team2, 'TeamA' AS winner, 'runs' AS outcome_type, 20.0::numeric AS target_overs, 180::numeric AS target_runs, FALSE AS is_dls_applied, NULL::boolean AS is_dls_abandoned, NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs, NULL::integer AS dls_par_score, TRUE AS scorecard_available, 'M1' AS source_note UNION ALL
    SELECT 'M2', '2026-02-11'::date, 'Group Stage', 'Group Stage', 'A', 'TeamA', 'TeamC', 'TeamA', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M2' UNION ALL
    SELECT 'M3', '2026-02-12'::date, 'Group Stage', 'Group Stage', 'A', 'TeamA', 'TeamD', 'TeamA', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M3' UNION ALL
    SELECT 'M4', '2026-02-13'::date, 'Group Stage', 'Group Stage', 'A', 'TeamA', 'TeamE', 'TeamA', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M4' UNION ALL
    SELECT 'M5', '2026-02-14'::date, 'Group Stage', 'Group Stage', 'A', 'TeamB', 'TeamC', 'TeamB', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M5' UNION ALL
    SELECT 'M6', '2026-02-15'::date, 'Group Stage', 'Group Stage', 'A', 'TeamB', 'TeamD', 'TeamB', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M6' UNION ALL
    SELECT 'M7', '2026-02-16'::date, 'Group Stage', 'Group Stage', 'A', 'TeamB', 'TeamE', 'TeamB', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M7' UNION ALL
    SELECT 'M8', '2026-02-17'::date, 'Group Stage', 'Group Stage', 'A', 'TeamC', 'TeamD', 'TeamC', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M8' UNION ALL
    SELECT 'M9', '2026-02-18'::date, 'Group Stage', 'Group Stage', 'A', 'TeamC', 'TeamE', 'TeamC', 'runs', 20.0, 160::numeric, FALSE, NULL, NULL, NULL, NULL, TRUE, 'M9' UNION ALL
    SELECT 'M10', '2026-02-19'::date, 'Group Stage', 'Group Stage', 'A', 'TeamD', 'TeamE', NULL::varchar, 'no result', NULL::numeric, NULL::numeric, TRUE, TRUE, NULL, NULL, NULL, TRUE, 'M10'
"""
summaries_sql = """
    SELECT 'M1' AS match_id, 1 AS innings, 'TeamA' AS batting_team, 'TeamB' AS bowling_team, 180 AS total_runs, 4 AS total_wickets, 120 AS legal_deliveries, FALSE AS is_super_over UNION ALL
    SELECT 'M1', 2, 'TeamB', 'TeamA', 150, 6, 120, FALSE UNION ALL
    SELECT 'M2', 1, 'TeamA', 'TeamC', 160, 4, 120, FALSE UNION ALL
    SELECT 'M2', 2, 'TeamC', 'TeamA', 130, 6, 120, FALSE UNION ALL
    SELECT 'M3', 1, 'TeamA', 'TeamD', 160, 4, 120, FALSE UNION ALL
    SELECT 'M3', 2, 'TeamD', 'TeamA', 130, 6, 120, FALSE UNION ALL
    SELECT 'M4', 1, 'TeamA', 'TeamE', 160, 4, 120, FALSE UNION ALL
    SELECT 'M4', 2, 'TeamE', 'TeamA', 130, 6, 120, FALSE UNION ALL
    SELECT 'M5', 1, 'TeamB', 'TeamC', 160, 4, 120, FALSE UNION ALL
    SELECT 'M5', 2, 'TeamC', 'TeamB', 130, 6, 120, FALSE UNION ALL
    SELECT 'M6', 1, 'TeamB', 'TeamD', 160, 4, 120, FALSE UNION ALL
    SELECT 'M6', 2, 'TeamD', 'TeamB', 130, 6, 120, FALSE UNION ALL
    SELECT 'M7', 1, 'TeamB', 'TeamE', 160, 4, 120, FALSE UNION ALL
    SELECT 'M7', 2, 'TeamE', 'TeamB', 130, 6, 120, FALSE UNION ALL
    SELECT 'M8', 1, 'TeamC', 'TeamD', 160, 4, 120, FALSE UNION ALL
    SELECT 'M8', 2, 'TeamD', 'TeamC', 130, 6, 120, FALSE UNION ALL
    SELECT 'M9', 1, 'TeamC', 'TeamE', 160, 4, 120, FALSE UNION ALL
    SELECT 'M9', 2, 'TeamE', 'TeamC', 130, 6, 120, FALSE UNION ALL
    SELECT 'M10', 1, 'TeamD', 'TeamE', 0, 0, 0, FALSE
"""
q = build_20cte_query(matches_sql, summaries_sql)
cur.execute(q)
rows = cur.fetchall()
print("Rows for Test 12:")
for r in rows:
    print(r)
conn.rollback()
conn.close()
