import psycopg2
import os
import re
import json
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

# 3A: Extract view columns
cur.execute("""
SELECT column_name, data_type, ordinal_position
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name='view_tournament_standings'
ORDER BY ordinal_position;
""")
view_cols = cur.fetchall()
view_col_names = [r[0] for r in view_cols]
print("=== 3A. View Columns in PostgreSQL ===")
for col, dt, pos in view_cols:
    print(f"{pos:>2}. {col:<25} ({dt})")

# 3B: Extract DAX measures
print("\n=== 3B. Scanning DAX Measures ===")
with open("power_bi/dax_measures.dax", encoding="utf-8") as f:
    dax_text = f.read()

# Find all Table[Column] references
table_col_refs = re.findall(r"('?[a-zA-Z0-9_ ]+'?)\[([a-zA-Z0-9_ ]+)\]", dax_text)
print(f"Total Table[Column] references in DAX: {len(table_col_refs)}")

standings_refs = set()
for tbl, col in table_col_refs:
    clean_tbl = tbl.strip("'").strip()
    if any(k in clean_tbl.lower() for k in ["standing", "tournament", "rank", "pool"]):
        standings_refs.add((clean_tbl, col))

print(f"Standings-specific references ({len(standings_refs)}):")
for tbl, col in sorted(standings_refs):
    print(f"   {tbl}[{col}]")

# Check all tables in model.bim
with open("power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim", encoding="utf-8") as f:
    bim = json.load(f)

print("\n=== 3C. Tables in model.bim ===")
for t in bim.get("model", {}).get("tables", []):
    name = t["name"]
    cols = [c["name"] for c in t.get("columns", [])]
    measures = [m["name"] for m in t.get("measures", [])]
    print(f"Table: {name} ({len(cols)} cols, {len(measures)} measures)")
    if any(k in name.lower() for k in ["standing", "tournament"]):
        print(f"   Columns: {cols}")
        for m in t.get("measures", []):
            print(f"   Measure '{m['name']}': {m.get('expression', '')[:80]}...")

# Also scan power_query_m_code.m
with open("power_bi/power_query_m_code.m", encoding="utf-8") as f:
    m_code = f.read()

print(f"\nPower Query M code length: {len(m_code)}")
for line in m_code.splitlines():
    if "standing" in line.lower() or "tournament" in line.lower() or "view_" in line.lower():
        print("M Code line:", line.strip())
