import psycopg2

conn = psycopg2.connect('dbname=t20_worldcup_2026 user=postgres password=Gautam@101 host=localhost port=5432')
cur = conn.cursor()

# Test gcd in transaction so we don't leave anything in production
cur.execute("BEGIN;")

gcd_ddl = """
CREATE OR REPLACE FUNCTION test_gcd(a NUMERIC, b NUMERIC)
RETURNS NUMERIC AS $$
DECLARE
    x NUMERIC;
    y NUMERIC;
    t NUMERIC;
BEGIN
    IF a IS NULL OR b IS NULL THEN
        RETURN NULL;
    END IF;
    -- Explicit integer-input validation: must not contain fractional part!
    IF a != TRUNC(a) OR b != TRUNC(b) THEN
        RAISE EXCEPTION 'gcd(NUMERIC, NUMERIC) requires integer inputs, received a=%, b=%', a, b;
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
$$ LANGUAGE plpgsql IMMUTABLE STRICT;
"""
cur.execute(gcd_ddl)

# 1. Test positive integers:
cur.execute("SELECT test_gcd(100, 180);")
res_pos = cur.fetchone()[0]
print(f"Positive gcd(100, 180) = {res_pos} (expected 20)")
assert res_pos == 20

# 2. Test negative integers:
cur.execute("SELECT test_gcd(-100, 180);")
res_neg = cur.fetchone()[0]
print(f"Negative gcd(-100, 180) = {res_neg} (expected 20)")
assert res_neg == 20

# 3. Test zero numerator:
cur.execute("SELECT test_gcd(0, 180);")
res_zero_num = cur.fetchone()[0]
print(f"Zero numerator gcd(0, 180) = {res_zero_num} (expected 180)")
assert res_zero_num == 180

# 4. Test zero denominator:
cur.execute("SELECT test_gcd(180, 0);")
res_zero_den = cur.fetchone()[0]
print(f"Zero denominator gcd(180, 0) = {res_zero_den} (expected 180)")
assert res_zero_den == 180

# 5. Test both zero:
cur.execute("SELECT test_gcd(0, 0);")
res_both_zero = cur.fetchone()[0]
print(f"Both zero gcd(0, 0) = {res_both_zero} (expected 1)")
assert res_both_zero == 1

# 6. Test invalid fractional input:
fractional_caught = False
try:
    cur.execute("SELECT test_gcd(10.5, 20);")
except Exception as e:
    fractional_caught = True
    print(f"Fractional input caught correctly: {e}")

assert fractional_caught, "Expected test_gcd(10.5, 20) to raise exception!"

# Rollback so zero test functions remain in DB:
conn.rollback()
conn.close()
print("All strict GCD unit tests passed successfully!")
