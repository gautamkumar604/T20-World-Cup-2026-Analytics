import psycopg2

PG_CONN_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 't20_worldcup_2026',
    'user': 'postgres',
    'password': 'Gautam@101'
}

conn = psycopg2.connect(**PG_CONN_PARAMS)
cur = conn.cursor()

cur.execute("BEGIN;")

gcd_ddl = """
CREATE OR REPLACE FUNCTION fn_calc_gcd(a bigint, b bigint)
RETURNS bigint AS $fn$
DECLARE
    x bigint;
    y bigint;
    t bigint;
BEGIN
    IF a IS NULL OR b IS NULL THEN
        RETURN NULL;
    END IF;
    IF a = -9223372036854775808 OR b = -9223372036854775808 THEN
        RAISE EXCEPTION 'fn_calc_gcd: INT64_MIN not supported';
    END IF;
    x := ABS(a);
    y := ABS(b);
    IF x = 0 AND y = 0 THEN
        RETURN 1;
    ELSIF x = 0 THEN
        RETURN y;
    ELSIF y = 0 THEN
        RETURN x;
    END IF;
    WHILE y != 0 LOOP
        t := y;
        y := x % y;
        x := t;
    END LOOP;
    RETURN x;
END;
$fn$ LANGUAGE plpgsql IMMUTABLE STRICT;
"""
cur.execute(gcd_ddl)

import sys
sys.path.append('.')
from scratch.test_phase4_9_6_15_audit import build_22cte_query

matches_current_sql = """
    SELECT match_id, match_date, stage, group_name, team1, team2, winner, outcome_type,
           target_overs, target_runs, is_dls_applied, NULL::boolean AS is_dls_abandoned,
           NULL::numeric AS dls_allocated_overs, NULL::numeric AS dls_abandonment_overs,
           NULL::integer AS dls_par_score, scorecard_available, source_note
    FROM dim_matches
"""
summaries_current_sql = """
    SELECT match_id, innings, batting_team, bowling_team, total_runs, total_wickets,
           legal_deliveries, total_overs, is_super_over
    FROM fact_match_summaries
"""
q_prod = build_22cte_query(matches_current_sql, summaries_current_sql)
q_prod = q_prod.replace('fn_calc_gcd(CAST(s.n AS NUMERIC), CAST(s.d AS NUMERIC))', 'fn_calc_gcd(CAST(s.n AS BIGINT), CAST(s.d AS BIGINT))')
cur.execute(q_prod)
prod_rows = cur.fetchall()

print(f"Total production rows returned: {len(prod_rows)}")
print("Stage        | Grp  | Rk  | Team                      | P  | W  | L  | NR | Pts | NRR     | Resolution Step                     | Status")
print("-" * 135)
for r in prod_rows:
    print(f"{r[0]:<12} | {r[1]:<4} | {r[2]:<3} | {r[3]:<25} | {r[4]:<2} | {r[5]:<2} | {r[6]:<2} | {r[7]:<2} | {r[8]:<3} | {str(r[9]):<7} | {r[13]:<37} | {r[14]}")

# Specifically check Zimbabwe and Pakistan:
zim_rows = [r for r in prod_rows if r[3] == 'Zimbabwe']
pak_rows = [r for r in prod_rows if r[3] == 'Pakistan']

print("\n=== ZIMBABWE IN STANDINGS ===")
for r in zim_rows:
    print(f"Stage: {r[0]}, Group: {r[1]}, Rank: {r[2]}, Pts: {r[8]}, NRR: {r[9]}, Status: {r[14]}")

print("\n=== PAKISTAN IN STANDINGS ===")
for r in pak_rows:
    print(f"Stage: {r[0]}, Group: {r[1]}, Rank: {r[2]}, Pts: {r[8]}, NRR: {r[9]}, Status: {r[14]}")

conn.rollback()
conn.close()
