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

# Test INT64_MIN:
try:
    cur.execute("SELECT fn_calc_gcd((-9223372036854775807::bigint - 1::bigint), 16::bigint);")
    print("INT64_MIN not caught!")
except Exception as e:
    print("INT64_MIN caught successfully:", e)

conn.rollback()
conn.close()
