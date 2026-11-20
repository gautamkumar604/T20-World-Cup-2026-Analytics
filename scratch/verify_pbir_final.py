import json
import os
import sys

BASE_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages'
BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'

errors = []

print("=== CHECK 1: TASK 1 (Total Tournament Runs #,##0 & 1D) ===")
with open(BIM_PATH, 'r', encoding='utf-8') as f:
    bim = json.load(f)

for t in bim['model']['tables']:
    for m in t.get('measures', []):
        if m['name'] == 'Total Tournament Runs':
            fmt = m.get('formatString')
            print(f"model.bim Total Tournament Runs formatString: '{fmt}'")
            if fmt != '#,##0':
                errors.append(f"formatString is '{fmt}', expected '#,##0'")

p3_card = os.path.join(BASE_DIR, 'ReportSection_Page3_ExecutiveOverview/visuals/Card_Exec_TotalRuns/visual.json')
with open(p3_card, 'r', encoding='utf-8') as f:
    c3 = json.load(f)
du3 = c3['visual']['objects']['labels'][0]['properties']['displayUnits']['expr']['Literal']['Value']
print(f"Card_Exec_TotalRuns displayUnits: {du3}")
if du3 != '1D':
    errors.append(f"Card_Exec_TotalRuns displayUnits is '{du3}', expected '1D'")

p1_card = os.path.join(BASE_DIR, 'ReportSection_Page1_Overview/visuals/Card_TotalRuns/visual.json')
with open(p1_card, 'r', encoding='utf-8') as f:
    c1 = json.load(f)
du1 = c1['visual']['objects']['labels'][0]['properties']['displayUnits']['expr']['Literal']['Value']
print(f"Card_TotalRuns (Page 1) displayUnits: {du1}")
if du1 != '1D':
    errors.append(f"Card_TotalRuns displayUnits is '{du1}', expected '1D'")

print("\n=== CHECK 2: TASK 2 (Strict Top 5 Filters on Page 3 Tables) ===")
p3_visuals_dir = os.path.join(BASE_DIR, 'ReportSection_Page3_ExecutiveOverview/visuals')
expected = {
    'Table_TopRunScorers': ('Top', 5, 'Player Total Runs'),
    'Table_TopWicketTakers': ('Top', 5, 'Player Total Wickets'),
    'Table_HighestStrikeRate': ('Top', 5, 'Player Strike Rate (Min 100 Runs)'),
    'Table_BestBowlingEconomy': ('Bottom', 5, 'Player Economy Rate (Min 10 Overs)')
}

for tname, (exp_op, exp_cnt, exp_meas) in expected.items():
    vpath = os.path.join(p3_visuals_dir, tname, 'visual.json')
    with open(vpath, 'r', encoding='utf-8') as f:
        vjson = json.load(f)
    
    fc = vjson.get('filterConfig', {}).get('filters', [])
    if not fc:
        errors.append(f"{tname} missing filterConfig.filters!")
        continue
    
    filt = fc[0]
    ftype = filt.get('type')
    op = filt.get('operator')
    cnt = filt.get('itemCount')
    meas = filt.get('orderBy', {}).get('Measure', {}).get('Property')
    
    print(f"{tname}: type={ftype}, operator={op}, count={cnt}, orderBy={meas}")
    if ftype != 'TopN' or op != exp_op or cnt != exp_cnt or meas != exp_meas:
        errors.append(f"{tname} filterConfig mismatch! Got {filt}")

print("\n=== CHECK 3: TASK 3 (Page 2 Matrix Conditional Formatting) ===")
matrix_path = os.path.join(BASE_DIR, 'ReportSection_Page2_Standings/visuals/Matrix_TournamentStandings/visual.json')
with open(matrix_path, 'r', encoding='utf-8') as f:
    mjson = json.load(f)

mobjs = mjson['visual'].get('objects', {})
vals = mobjs.get('values', [])
if not vals:
    errors.append("Matrix objects.values is missing!")
else:
    found_rules = False
    for v_entry in vals:
        props = v_entry.get('properties', {})
        if 'backColor' in props and 'rules' in props['backColor']:
            rules_obj = props['backColor']['rules']
            in_prop = rules_obj.get('input', {}).get('Column', {}).get('Property')
            rule_list = rules_obj.get('rules', [])
            rule_map = {r['value']: r['color']['solid']['color'] for r in rule_list}
            print(f"Matrix backColor conditional rules input='{in_prop}', rules={rule_map}")
            if in_prop == 'qualification_status' and rule_map.get('Qualified') == '#D4EDDA' and rule_map.get('Eliminated') == '#E9ECEF':
                found_rules = True
    if not found_rules:
        errors.append("Matrix conditional formatting rules for qualification_status not found in values.backColor!")

print("\n=== CHECK 4: JSON VALIDITY OF ALL PBIR FILES ===")
json_count = 0
for root, dirs, files in os.walk('power_bi'):
    for f in files:
        if f.endswith('.json') or f.endswith('.bim') or f.endswith('.pbip') or f.endswith('.pbir'):
            fpath = os.path.join(root, f)
            with open(fpath, 'r', encoding='utf-8') as fp:
                json.load(fp)
            json_count += 1

print(f"Successfully validated syntax of all {json_count} JSON/BIM/PBIR/PBIP files!")

print(f"\nTOTAL AUDIT ERRORS: {len(errors)}")
if errors:
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL 3 TASKS STRICTLY VERIFIED WITH ZERO ERRORS!")
