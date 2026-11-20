import json
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("POWER BI PBIP STRUCTURAL & DATA BINDING INTEGRITY VALIDATOR")
print("="*60)

BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'
REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'

# 1. Parse model.bim
with open(BIM_PATH, 'r', encoding='utf-8') as f:
    bim = json.load(f)

print("[1] model.bim JSON Syntax: VALID")
tables = {t['name']: t for t in bim['model']['tables']}
print(f"    Total tables: {len(tables)}")
assert 'view_tournament_standings' in tables, "view_tournament_standings table missing"

st_table = tables['view_tournament_standings']
st_cols = {c['name']: c for c in st_table['columns']}
print(f"    view_tournament_standings columns: {len(st_cols)}")

# Check dataTypes of Fix 1
for col in ['nrr_num', 'nrr_den', 'nrr_canon_num', 'nrr_canon_den']:
    dtype = st_cols[col]['dataType']
    print(f"    Column '{col}' dataType: {dtype}")
    assert dtype == 'int64', f"Expected int64 for {col}, got {dtype}"

assert st_cols['nrr_display']['dataType'] == 'double', "Expected double for nrr_display"
print("[1.1] Fix 1 dataType check: PASS (All 4 rational columns Int64, nrr_display Double)")

# 2. Parse report.json
with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    rep = json.load(f)

print("\n[2] report.json JSON Syntax: VALID")
sections = {s['name']: s for s in rep['sections']}
print(f"    Total sections: {len(sections)} -> {[s['displayName'] for s in rep['sections']]}")
assert 'ReportSection_Page2_Standings' in sections, "Standings page missing"

st_sec = sections['ReportSection_Page2_Standings']
print(f"    Standings page visualContainers: {len(st_sec['visualContainers'])}")

# Check every visual container config and ensure all queryRefs exist in model.bim
all_query_refs = []
for i, vc in enumerate(st_sec['visualContainers']):
    cfg = json.loads(vc['config'])
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')
    vname = cfg.get('name')
    print(f"    Visual {i+1} [{vtype}]: {vname}")
    projections = sv.get('projections', {})
    for role, items in projections.items():
        for item in items:
            qref = item.get('queryRef')
            if qref:
                all_query_refs.append((vname, role, qref))

print(f"\n[3] Total queryRefs on Standings Page: {len(all_query_refs)}")
unresolved_refs = []
for vname, role, qref in all_query_refs:
    tbl, col = qref.split('.')
    if tbl not in tables:
        unresolved_refs.append((vname, role, qref, "Table not in model"))
    elif col not in [c['name'] for c in tables[tbl]['columns']]:
        unresolved_refs.append((vname, role, qref, "Column not in table"))

if unresolved_refs:
    print("  [FAIL] Unresolved queryRefs:", unresolved_refs)
    assert False, "Found unresolved queryRefs"
else:
    print("  [PASS] 100% of visual queryRefs resolve to existing model columns!")

# 4. Simulate visual rendering against PostgreSQL live data
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', ''),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

# Simulation 1: Slicer = 'All'
cur.execute("""
SELECT stage_normalized, group_name, pool_rank, team_name, played, wins, losses, no_result, points, nrr_display, qualification_status
FROM view_tournament_standings
ORDER BY stage_normalized, group_name, pool_rank;
""")
all_standings = cur.fetchall()
print(f"\n[4.1] Simulated Visual Output with Slicer = 'All': {len(all_standings)} rows rendered")
assert len(all_standings) == 28

# Simulation 2: Slicer = 'Group Stage'
gs_standings = [r for r in all_standings if r[0] == 'Group Stage']
print(f"[4.2] Simulated Visual Output with Slicer = 'Group Stage': {len(gs_standings)} rows rendered")
assert len(gs_standings) == 20

# Simulation 3: Slicer = 'Super 8'
s8_standings = [r for r in all_standings if r[0] == 'Super 8']
print(f"[4.3] Simulated Visual Output with Slicer = 'Super 8': {len(s8_standings)} rows rendered")
assert len(s8_standings) == 8

# Simulation 4: Slicer = 'Group D'
d_standings = [r for r in all_standings if r[0] == 'Group Stage' and r[1] == 'D']
print(f"[4.4] Simulated Visual Output with Slicer = 'Group D': {len(d_standings)} rows rendered")
assert len(d_standings) == 5
assert d_standings[0][3] == 'South Africa' and d_standings[0][2] == 1
assert d_standings[1][3] == 'New Zealand' and d_standings[1][2] == 2

print("\n" + "="*60)
print("ALL PBIP VALIDATIONS & VISUAL RENDER SIMULATIONS PASSED (100%)")
print("="*60)
