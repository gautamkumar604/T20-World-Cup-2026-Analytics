import psycopg2
import sys
sys.path.append('.')
from scratch.test_phase15_comprehensive import get_pg_conn, get_full_22cte_sql

conn = get_pg_conn()
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
    IF a = (-9223372036854775807 - 1) OR b = (-9223372036854775807 - 1) THEN
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

cur.execute("""
    CREATE SCHEMA temp_validation_schema;
    CREATE TABLE temp_validation_schema.dim_matches (LIKE public.dim_matches INCLUDING ALL);
    ALTER TABLE temp_validation_schema.dim_matches 
        ADD COLUMN is_dls_abandoned boolean,
        ADD COLUMN dls_allocated_overs numeric(4,1),
        ADD COLUMN dls_abandonment_overs numeric(4,1),
        ADD COLUMN dls_par_score integer;
    INSERT INTO temp_validation_schema.dim_matches 
    SELECT *, NULL::boolean, NULL::numeric, NULL::numeric, NULL::integer FROM public.dim_matches;
    CREATE TABLE temp_validation_schema.fact_match_summaries (LIKE public.fact_match_summaries INCLUDING ALL);
    INSERT INTO temp_validation_schema.fact_match_summaries SELECT * FROM public.fact_match_summaries;
    SET search_path = temp_validation_schema, public;
""")
raw_view_ddl = f"CREATE OR REPLACE VIEW temp_validation_schema.view_tournament_standings AS {get_full_22cte_sql('temp_validation_schema.dim_matches', 'temp_validation_schema.fact_match_summaries')}"
cur.execute(raw_view_ddl)
cur.execute("SELECT stage_normalized, group_name, count(*) FROM temp_validation_schema.view_tournament_standings GROUP BY stage_normalized, group_name ORDER BY 1, 2;")
rows = cur.fetchall()
print("Groups returned:")
for r in rows:
    print(r)

conn.rollback()
conn.close()
