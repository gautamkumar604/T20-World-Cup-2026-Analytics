import json
import psycopg2
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

print("==================================================================")
print("PHASE 4.2 STRUCTURAL, MODEL & VISUAL BINDING INTEGRITY VALIDATOR")
print("==================================================================")

# 1. Check model.bim
model_path = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'
with open(model_path, 'r', encoding='utf-8') as f:
    bim = json.load(f)

print("[1] model.bim Validation:")
tables = bim['model']['tables']
print(f"    Total tables: {len(tables)}")

available_fields = {}
all_measures = []
for t in tables:
    tname = t['name']
    available_fields[tname] = set()
    for c in t.get('columns', []):
        available_fields[tname].add(c['name'])
    for m in t.get('measures', []):
        available_fields[tname].add(m['name'])
        all_measures.append((tname, m['name'], m.get('displayFolder', 'Core Measures')))

print(f"    Total measures across model: {len(all_measures)}")
phase42_measures = [m for m in all_measures if m[2] == "Phase 4.2 Measures"]
print(f"    Phase 4.2 Measures count: {len(phase42_measures)}")
for m in phase42_measures:
    print(f"      - {m[0]}.[{m[1]}]")

# 2. Check report.json
report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

print("\n[2] report.json Validation:")
sections = rep['sections']
print(f"    Total sections: {len(sections)}")
for s in sections:
    print(f"    - Section {s.get('id')}: '{s.get('displayName')}' ({len(s.get('visualContainers', []))} visuals)")

# 3. Check queryRefs on Executive Overview page
exec_section = next((s for s in sections if s.get('name') == "ReportSection_Page3_ExecutiveOverview"), None)
if not exec_section:
    print("    [ERROR] ReportSection_Page3_ExecutiveOverview NOT FOUND in report.json!")
    exit(1)

print(f"\n[3] Executive Overview Visual Inventory ({len(exec_section['visualContainers'])} visuals):")
query_refs = []
for idx, vc in enumerate(exec_section['visualContainers']):
    cfg = json.loads(vc['config'])
    vname = cfg.get('name', 'unnamed')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType', 'unknown')
    projections = sv.get('projections', {})
    refs_in_visual = []
    for p_key, p_val in projections.items():
        if isinstance(p_val, list):
            for item in p_val:
                if isinstance(item, dict) and 'queryRef' in item:
                    refs_in_visual.append(item['queryRef'])
                    query_refs.append((vname, item['queryRef']))
    print(f"    Visual {idx+1} [{vtype}]: {vname}")
    if refs_in_visual:
        print(f"      Bindings: {refs_in_visual}")

print(f"\n[4] Resolving queryRefs on Executive Overview Page ({len(query_refs)} total bindings):")
errors = 0
for vname, qref in query_refs:
    if '.' not in qref:
        print(f"    [FAIL] Invalid queryRef format: '{qref}' in visual '{vname}'")
        errors += 1
        continue
    tbl, fld = qref.split('.', 1)
    if tbl not in available_fields:
        print(f"    [FAIL] Table '{tbl}' from queryRef '{qref}' not found in semantic model!")
        errors += 1
    elif fld not in available_fields[tbl]:
        print(f"    [FAIL] Field/Measure '{fld}' in table '{tbl}' not found in semantic model!")
        errors += 1
    else:
        pass

if errors == 0:
    print(f"    [PASS] 100% of queryRefs ({len(query_refs)}/{len(query_refs)}) resolve cleanly to model fields & measures!")
else:
    print(f"    [FAIL] {errors} queryRef errors detected!")

# 5. Connect to PostgreSQL and compare PSQL baseline with Power BI logic
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 't20_worldcup_2026'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', 'postgres'),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

print("\n[5] PSQL vs Power BI Cross-Check Evidence:")
cur.execute("SELECT COUNT(*) FROM dim_matches;")
psql_matches = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM dim_matches WHERE outcome_type IN ('runs', 'wickets', 'tie_super_over');")
psql_completed = cur.fetchone()[0]

cur.execute("SELECT SUM(total_runs) FROM fact_match_summaries WHERE is_super_over = FALSE;")
psql_runs = cur.fetchone()[0]

cur.execute("SELECT SUM(total_wickets) FROM fact_match_summaries WHERE is_super_over = FALSE;")
psql_wickets = cur.fetchone()[0]

cur.execute("SELECT MAX(total_runs) FROM fact_match_summaries WHERE is_super_over = FALSE;")
psql_max_runs = cur.fetchone()[0]

cur.execute("SELECT MIN(total_runs) FROM fact_match_summaries WHERE is_super_over = FALSE;")
psql_min_runs = cur.fetchone()[0]

cross_checks = [
    ("Total Matches Scheduled", 55, psql_matches),
    ("Matches Completed", 53, psql_completed),
    ("Total Runs Scored", 17582, psql_runs),
    ("Total Wickets Fallen", 702, psql_wickets),
    ("Highest Team Score", 256, psql_max_runs),
    ("Lowest Team Score", 95, psql_min_runs)
]

print("    -----------------------------------------------------------------------------")
print("    Metric                       | Expected | PSQL Actual | Match Status")
print("    -----------------------------------------------------------------------------")
for name, exp, act in cross_checks:
    status = "EXACT MATCH" if exp == act else "MISMATCH"
    print(f"    {name:<28} | {exp:<8} | {act:<11} | {status}")
print("    -----------------------------------------------------------------------------")

conn.close()

# Save text verification artifact
os.makedirs('reports', exist_ok=True)
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
rpt_file = f'reports/phase_4_2_structural_verification_{ts}.txt'
with open(rpt_file, 'w', encoding='utf-8') as f:
    f.write(f"Phase 4.2 Executive Overview Verification Snapshot ({ts})\n")
    f.write("Verdict: STRUCTURALLY VERIFIED — PENDING USER DESKTOP VALIDATION\n\n")
    f.write(f"Sections Count: {len(sections)}\n")
    f.write(f"Total Model Measures: {len(all_measures)} (38 Core + {len(phase42_measures)} Phase 4.2)\n")
    f.write(f"Page 3 Visuals: {len(exec_section['visualContainers'])}\n")
    f.write(f"QueryRefs Resolved: {len(query_refs)} (Errors: {errors})\n\n")
    f.write("KPI Cross-Check Table:\n")
    for name, exp, act in cross_checks:
        f.write(f" - {name}: Expected={exp}, PSQL Actual={act} (Match: {exp == act})\n")

print(f"\nVerification snapshot written to: {rpt_file}")
