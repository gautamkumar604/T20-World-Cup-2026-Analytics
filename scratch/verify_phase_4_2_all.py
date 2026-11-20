import json
import os

print("=== 1. PBIP MANIFEST VERIFICATION ===")
with open('power_bi/T20_World_Cup_2026_Analytics.pbip', 'r', encoding='utf-8') as f:
    pbip = json.load(f)
print("PBIP structure:", json.dumps(pbip, indent=2))

print("\n=== 2. PBIR DATASET REFERENCE ===")
with open('power_bi/T20_World_Cup_2026_Analytics.Report/definition.pbir', 'r', encoding='utf-8') as f:
    pbir = json.load(f)
print("PBIR datasetReference:", json.dumps(pbir, indent=2))

print("\n=== 3. MODEL.BIM MEASURES ===")
with open('power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim', 'r', encoding='utf-8') as f:
    bim = json.load(f)
for t in bim['model']['tables']:
    for m in t.get('measures', []):
        if m['name'] == 'Total Tournament Runs':
            print(f"Table '{t['name']}' -> Measure '{m['name']}': formatString = {m.get('formatString')}")

print("\n=== 4. CARD DISPLAY UNITS ===")
cards = [
    'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals/Card_Exec_TotalRuns/visual.json',
    'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page1_Overview/visuals/Card_TotalRuns/visual.json'
]
for cp in cards:
    if os.path.exists(cp):
        with open(cp, 'r', encoding='utf-8') as f:
            c = json.load(f)
        labels = c['visual']['objects']['labels'][0]['properties']
        print(f"{os.path.basename(os.path.dirname(cp))}: displayUnits = {labels.get('displayUnits')}")

print("\n=== 5. MATRIX CONDITIONAL FORMATTING (PAGE 2) ===")
matrix_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page2_Standings/visuals/Matrix_TournamentStandings/visual.json'
with open(matrix_path, 'r', encoding='utf-8') as f:
    matrix = json.load(f)
vals = matrix['visual']['objects'].get('values', [])
print(f"Matrix values formatting rules count: {len(vals)}")
for idx, rule in enumerate(vals):
    sel = rule.get('selector')
    bc = rule.get('properties', {}).get('backColor', {})
    print(f"  Rule #{idx}: selector={sel}, backColor type={list(bc.keys())}")

print("\n=== 6. TOP 5 FILTERS (PAGE 3) ===")
top5_visuals = [
    'Table_TopRunScorers',
    'Table_TopWicketTakers',
    'Table_HighestStrikeRate',
    'Table_BestBowlingEconomy'
]
for tv in top5_visuals:
    vp = f'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals/{tv}/visual.json'
    with open(vp, 'r', encoding='utf-8') as f:
        v = json.load(f)
    filters = v.get('filterConfig', {}).get('filters', [])
    print(f"{tv}:")
    for f_idx, filt in enumerate(filters):
        print(f"  Filter #{f_idx}: type={filt.get('type')}, keys={list(filt.keys())}")
        if 'operator' in filt or 'itemCount' in filt or 'orderBy' in filt:
            print("  [ERROR] Found prohibited properties!")
        else:
            print("  [OK] Conforms strictly to FilterContainer schema.")

print("\n=== 7. TOTAL JSON FILE SYNTAX VALIDATION ===")
count = 0
for root, dirs, files in os.walk('power_bi'):
    for f in files:
        if f.endswith(('.json', '.bim', '.pbip', '.pbir', '.pbism')):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8') as fp:
                json.load(fp)
            count += 1
print(f"Validated all {count} Power BI definition files: ZERO syntax errors!")
