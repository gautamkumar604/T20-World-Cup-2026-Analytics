import json
import sys

REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'

with open(BIM_PATH, 'r', encoding='utf-8') as f:
    bim = json.load(f)

with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    rep = json.load(f)

# Extract BIM catalog
tables = {}
for t in bim['model']['tables']:
    tname = t['name']
    tables[tname] = {'columns': set(), 'measures': set()}
    for c in t.get('columns', []):
        tables[tname]['columns'].add(c['name'])
    for m in t.get('measures', []):
        tables[tname]['measures'].add(m['name'])

total_visuals = 0
total_bindings = 0
errors = []

for s_idx, sec in enumerate(rep['sections']):
    s_name = sec.get('name')
    s_disp = sec.get('displayName')
    print(f"\n=======================================================")
    print(f"VERIFYING SECTION {s_idx + 1}: {s_disp} ({s_name})")
    print(f"=======================================================")
    
    for v_idx, vc in enumerate(sec.get('visualContainers', [])):
        total_visuals += 1
        cfg = json.loads(vc['config'])
        vname = cfg.get('name')
        sv = cfg.get('singleVisual', {})
        vtype = sv.get('visualType')
        
        if vtype == 'textbox':
            print(f"  [OK] Visual {v_idx + 1}: {vname} (textbox) - static content")
            continue
            
        projections = sv.get('projections', {})
        pq = sv.get('prototypeQuery')
        
        if not pq:
            errors.append(f"Section '{s_disp}', Visual '{vname}' missing prototypeQuery!")
            print(f"  [FAIL] Visual {v_idx + 1}: {vname} ({vtype}) - MISSING prototypeQuery!")
            continue
            
        pq_select_names = {item['Name']: item for item in pq.get('Select', [])}
        
        # Verify projections vs prototypeQuery
        proj_qrefs = []
        for prop_key, p_list in projections.items():
            for p in p_list:
                qref = p.get('queryRef')
                proj_qrefs.append((prop_key, qref))
                total_bindings += 1
                
                # Check 1: queryRef is in prototypeQuery.Select
                if qref not in pq_select_names:
                    errors.append(f"Visual '{vname}': queryRef '{qref}' not found in prototypeQuery.Select!")
                    print(f"    [ERR] queryRef '{qref}' not in prototypeQuery.Select!")
                else:
                    # Check 2: Exists in model.bim
                    parts = qref.split('.', 1)
                    tname, prop = parts[0], parts[1]
                    if tname not in tables:
                        errors.append(f"Visual '{vname}': Table '{tname}' not in model.bim!")
                    else:
                        is_col = prop in tables[tname]['columns']
                        is_meas = prop in tables[tname]['measures']
                        if not is_col and not is_meas:
                            errors.append(f"Visual '{vname}': '{qref}' not found in model.bim (table {tname})!")
                        else:
                            # Check 3: AST node type matches bim (Measure vs Column)
                            sel_item = pq_select_names[qref]
                            if is_meas and 'Measure' not in sel_item:
                                errors.append(f"Visual '{vname}': '{qref}' is a Measure in BIM, but prototypeQuery does not use Measure node!")
                            elif is_col and 'Column' not in sel_item:
                                errors.append(f"Visual '{vname}': '{qref}' is a Column in BIM, but prototypeQuery does not use Column node!")

        print(f"  [OK] Visual {v_idx + 1}: {vname} ({vtype}) - {len(proj_qrefs)} bindings verified")
        if 'OrderBy' in pq:
            print(f"       OrderBy: {len(pq['OrderBy'])} expressions, Take: {pq.get('Take')}")

# Polish verification
print("\n=======================================================")
print("POLISH VERIFICATION CHECKS")
print("=======================================================")

s0 = rep['sections'][0]
s1 = rep['sections'][1]
s2 = rep['sections'][2]

# Page 3 Run Card
c_exec_runs = None
for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    if cfg.get('name') == 'Card_Exec_TotalRuns':
        c_exec_runs = cfg
        break

if c_exec_runs:
    labels = c_exec_runs['singleVisual']['objects']['labels'][0]['properties']
    unit_val = labels.get('displayUnits', {}).get('expr', {}).get('Literal', {}).get('Value')
    print(f"Card_Exec_TotalRuns displayUnits: {unit_val} (Expected '1D')")
    if unit_val != '1D':
        errors.append(f"Card_Exec_TotalRuns displayUnits is {unit_val}, expected '1D'")
else:
    errors.append("Card_Exec_TotalRuns not found!")

# Page 1 Run Card
c_p1_runs = None
for vc in s0['visualContainers']:
    cfg = json.loads(vc['config'])
    if cfg.get('name') == 'Card_TotalRuns':
        c_p1_runs = cfg
        break

if c_p1_runs:
    labels = c_p1_runs['singleVisual']['objects']['labels'][0]['properties']
    unit_val = labels.get('displayUnits', {}).get('expr', {}).get('Literal', {}).get('Value')
    print(f"Card_TotalRuns (Page 1) displayUnits: {unit_val} (Expected '1D')")
    if unit_val != '1D':
        errors.append(f"Card_TotalRuns displayUnits is {unit_val}, expected '1D'")
else:
    errors.append("Card_TotalRuns not found!")

# Player Tables Top 5 & OrderBy
expected_tables = {
    'Table_TopRunScorers': ('fact_batting_scorecards.Player Total Runs', 'Descending', 2, 5),
    'Table_TopWicketTakers': ('fact_bowling_scorecards.Player Total Wickets', 'Descending', 2, 5),
    'Table_HighestStrikeRate': ('fact_batting_scorecards.Player Strike Rate (Min 100 Runs)', 'Descending', 2, 5),
    'Table_BestBowlingEconomy': ('fact_bowling_scorecards.Player Economy Rate (Min 10 Overs)', 'Ascending', 1, 5)
}

for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    if vname in expected_tables:
        qref, exp_dir_str, exp_dir_int, exp_take = expected_tables[vname]
        sv = cfg['singleVisual']
        sd = sv.get('sortDefinition', {})
        sorts = sd.get('sort', [])
        if not sorts or sorts[0]['field']['queryRef'] != qref or sorts[0]['direction'] != exp_dir_str:
            errors.append(f"{vname}: sortDefinition mismatch! Got {sorts}")
        else:
            print(f"{vname}: sortDefinition OK ({qref} {exp_dir_str})")
            
        pq = sv.get('prototypeQuery', {})
        obs = pq.get('OrderBy', [])
        if not obs or obs[0]['Direction'] != exp_dir_int:
            errors.append(f"{vname}: prototypeQuery.OrderBy mismatch! Got {obs}")
        else:
            print(f"{vname}: prototypeQuery.OrderBy OK (Direction {exp_dir_int})")
            
        take = pq.get('Take')
        if take != exp_take:
            errors.append(f"{vname}: prototypeQuery.Take is {take}, expected {exp_take}")
        else:
            print(f"{vname}: prototypeQuery.Take OK ({take})")

print(f"\nTotal Visuals Scanned: {total_visuals}")
print(f"Total Visual Bindings Verified: {total_bindings}")
print(f"Total Errors Found: {len(errors)}")

if errors:
    print("\nERRORS:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("\nALL VERIFICATIONS PASSED WITH ZERO ERRORS!")
