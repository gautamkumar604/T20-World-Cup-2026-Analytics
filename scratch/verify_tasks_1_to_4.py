import json
import sys

REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'

with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    rep = json.load(f)

with open(BIM_PATH, 'r', encoding='utf-8') as f:
    bim = json.load(f)

errors = []

print("=== CHECK 1: TASK 1 (Number Formatting & Truncation) ===")
# Check model.bim formatString
found_fmt = False
for t in bim['model']['tables']:
    for m in t.get('measures', []):
        if m['name'] == 'Total Tournament Runs':
            found_fmt = True
            fmt = m.get('formatString')
            print(f"model.bim Total Tournament Runs formatString: '{fmt}'")
            if fmt != '#,##0':
                errors.append(f"model.bim Total Tournament Runs formatString is '{fmt}', expected '#,##0'")

if not found_fmt:
    errors.append("model.bim Total Tournament Runs measure not found!")

# Check Card_TotalRuns and Card_HighestScore on Page 1
s0 = rep['sections'][0]
for vc in s0['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    if vname == 'Card_TotalRuns':
        du = cfg['singleVisual']['objects']['labels'][0]['properties']['displayUnits']['expr']['Literal']['Value']
        print(f"Page 1 Card_TotalRuns displayUnits: {du}")
        if du != '1D':
            errors.append(f"Page 1 Card_TotalRuns displayUnits is '{du}', expected '1D'")
    elif vname == 'Card_HighestScore':
        w = vc.get('width')
        fs = cfg['singleVisual']['objects']['labels'][0]['properties']['fontSize']['expr']['Literal']['Value']
        print(f"Page 1 Card_HighestScore width: {w}, fontSize: {fs}")
        if w < 250:
            errors.append(f"Page 1 Card_HighestScore width {w} is too small (<250)")

# Check Card_Exec_HighestScore on Page 3
s2 = rep['sections'][2]
for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    if vname == 'Card_Exec_TotalRuns':
        du = cfg['singleVisual']['objects']['labels'][0]['properties']['displayUnits']['expr']['Literal']['Value']
        print(f"Page 3 Card_Exec_TotalRuns displayUnits: {du}")
        if du != '1D':
            errors.append(f"Page 3 Card_Exec_TotalRuns displayUnits is '{du}', expected '1D'")
    elif vname == 'Card_Exec_HighestScore':
        w = vc.get('width')
        fs = cfg['singleVisual']['objects']['labels'][0]['properties']['fontSize']['expr']['Literal']['Value']
        print(f"Page 3 Card_Exec_HighestScore width: {w}, fontSize: {fs}")
        if w < 240:
            errors.append(f"Page 3 Card_Exec_HighestScore width {w} is too small (<240)")

print("\n=== CHECK 2: TASK 2 (Overlap & Layout Verification) ===")
# Algorithmic collision detection for visual containers
for s_idx, sec in enumerate(rep['sections']):
    sec_name = sec.get('displayName')
    vcs = sec.get('visualContainers', [])
    print(f"\nChecking section {sec_name} ({len(vcs)} visuals) for collisions:")
    collisions = 0
    for i in range(len(vcs)):
        cfg_i = json.loads(vcs[i]['config'])
        name_i = cfg_i.get('name')
        xi1, yi1 = vcs[i]['x'], vcs[i]['y']
        xi2, yi2 = xi1 + vcs[i]['width'], yi1 + vcs[i]['height']
        
        for j in range(i + 1, len(vcs)):
            cfg_j = json.loads(vcs[j]['config'])
            name_j = cfg_j.get('name')
            xj1, yj1 = vcs[j]['x'], vcs[j]['y']
            xj2, yj2 = xj1 + vcs[j]['width'], yj1 + vcs[j]['height']
            
            # Intersection test
            overlap_x = max(0, min(xi2, xj2) - max(xi1, xj1))
            overlap_y = max(0, min(yi2, yj2) - max(yi1, yj1))
            if overlap_x > 0 and overlap_y > 0:
                collisions += 1
                errors.append(f"Section {sec_name}: Overlap between '{name_i}' and '{name_j}' ({overlap_x}x{overlap_y} px)")
                print(f"  [COLLISION] {name_i} and {name_j} overlap by {overlap_x}x{overlap_y} px")
    if collisions == 0:
        print(f"  [OK] 0 collisions detected across all visuals in {sec_name}!")

# Verify table heights on Page 3
for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    if 'Table_' in vname:
        h = vc.get('height')
        print(f"Page 3 {vname} height: {h}")
        if h < 320:
            errors.append(f"{vname} height {h} is too small (<320)")

print("\n=== CHECK 3: TASK 3 (Top 5 Filters on Page 3) ===")
expected_top5 = ['Table_TopRunScorers', 'Table_TopWicketTakers', 'Table_HighestStrikeRate', 'Table_BestBowlingEconomy']
for vc in s2['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    if vname in expected_top5:
        # Check vc.filters
        if 'filters' not in vc:
            errors.append(f"{vname} missing vc.filters!")
        else:
            filt = json.loads(vc['filters'])
            print(f"{vname} vc.filters: type={filt[0].get('type')}, count={filt[0].get('itemCount')}, op={filt[0].get('operator')}")
            if filt[0].get('itemCount') != 5 or filt[0].get('type') != 'TopN':
                errors.append(f"{vname} filter invalid: {filt}")
        # Check cfg.filterConfig
        if 'filterConfig' not in cfg:
            errors.append(f"{vname} missing cfg.filterConfig!")
        else:
            fc = cfg['filterConfig']
            if fc[0].get('itemCount') != 5:
                errors.append(f"{vname} filterConfig itemCount != 5")
        # Check prototypeQuery.Take
        take = cfg['singleVisual']['prototypeQuery'].get('Take')
        if take != 5:
            errors.append(f"{vname} prototypeQuery.Take is {take}, expected 5")

print("\n=== CHECK 4: TASK 4 (Matrix Stepped Layout & Formatting) ===")
s1 = rep['sections'][1]
for vc in s1['visualContainers']:
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    if vname == 'Matrix_TournamentStandings':
        sv = cfg['singleVisual']
        objs = sv.get('objects', {})
        stepped = objs.get('rowHeaders', [{}])[0].get('properties', {}).get('stepped', {}).get('expr', {}).get('Literal', {}).get('Value')
        print(f"Matrix_TournamentStandings rowHeaders.stepped: {stepped}")
        if stepped != 'true':
            errors.append(f"Matrix stepped layout not true: {stepped}")
        
        cf = objs.get('conditionalFormatting', [])
        print(f"Matrix_TournamentStandings conditionalFormatting entries: {len(cf)}")
        if not cf:
            errors.append("Matrix conditionalFormatting missing!")
            
    elif vname == 'Slicer_Group_Standings':
        sv = cfg['singleVisual']
        mode = sv.get('objects', {}).get('data', [{}])[0].get('properties', {}).get('mode', {}).get('expr', {}).get('Literal', {}).get('Value')
        print(f"Slicer_Group_Standings mode: {mode}")
        if mode != "'Dropdown'":
            errors.append(f"Slicer_Group_Standings mode is {mode}, expected 'Dropdown'")

print("\n=======================================================")
print(f"TOTAL ERRORS FOUND: {len(errors)}")
if errors:
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL 4 TASKS VERIFIED WITH ZERO ERRORS AND ZERO OVERLAPS!")
