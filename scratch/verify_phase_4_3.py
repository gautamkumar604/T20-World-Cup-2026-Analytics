import json
import os

print("=== 1. VERIFY PAGES.JSON ===")
pages_json_path = "power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/pages.json"
with open(pages_json_path, 'r', encoding='utf-8') as f:
    pages_meta = json.load(f)
print("Page Order:", pages_meta.get("pageOrder"))
assert "ReportSection_Page4_TacticalAnalysis" in pages_meta.get("pageOrder"), "Page 4 missing from pages.json!"

print("\n=== 2. VERIFY PAGE 4 CONFIGURATION & VISUALS ===")
p4_dir = "power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page4_TacticalAnalysis"
with open(f"{p4_dir}/page.json", 'r', encoding='utf-8') as f:
    page_data = json.load(f)
print(f"Page Name: {page_data.get('name')}, Display: {page_data.get('displayName')}")

visuals_dir = f"{p4_dir}/visuals"
visual_folders = os.listdir(visuals_dir)
print(f"Total Visuals on Page 4: {len(visual_folders)}")

for vf in visual_folders:
    v_path = f"{visuals_dir}/{vf}/visual.json"
    with open(v_path, 'r', encoding='utf-8') as f:
        v_data = json.load(f)
    vt = v_data.get("visual", {}).get("visualType")
    pos = v_data.get("position", {})
    qs = v_data.get("visual", {}).get("query", {}).get("queryState", {})
    channels = list(qs.keys())
    print(f" - {vf} ({vt}): pos=({pos.get('x')}, {pos.get('y')}, w={pos.get('width')}, h={pos.get('height')}) | channels={channels}")
    
    # Check for invalid filter properties
    fc = v_data.get("filterConfig", {})
    for filt in fc.get("filters", []):
        for bad_key in ['operator', 'itemCount', 'orderBy']:
            assert bad_key not in filt, f"Found illegal key '{bad_key}' in {vf} filter!"

print("\n=== 3. VERIFY MODEL.BIM ADDITIONS ===")
bim_path = "power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim"
with open(bim_path, 'r', encoding='utf-8') as f:
    bim = json.load(f)

# Check dim_matches
for t in bim['model']['tables']:
    if t['name'] == 'dim_matches':
        cols = {c['name']: c for c in t.get('columns', [])}
        measures = {m['name']: m for m in t.get('measures', [])}
        print("dim_matches columns added:")
        for cn in ['Toss Decision Label', 'Toss Match Result']:
            print(f"  - {cn}: type={cols[cn].get('type')}, expression={cols[cn].get('expression')}")
        print("dim_matches measures added:")
        print(f"  - Toss Completed Matches: {measures.get('Toss Completed Matches', {}).get('expression')}")

    if t['name'] == 'fact_deliveries':
        measures = {m['name']: m for m in t.get('measures', [])}
        print(f"\nfact_deliveries total measures: {len(measures)}")
        for mn in [
            'Powerplay Run Rate', 'Powerplay Wickets',
            'Middle Overs Run Rate', 'Middle Overs Wickets',
            'Death Overs Run Rate', 'Death Overs Wickets',
            'Phase Total Fours', 'Phase Total Sixes', 'Phase Total Boundaries',
            'Bowler Powerplay Wickets', 'Bowler Powerplay Overs', 'Bowler Powerplay Economy',
            'Bowler Death Overs Economy (Min 10 Balls)', 'Bowler Death Overs Wickets', 'Bowler Death Overs Balls'
        ]:
            assert mn in measures, f"Missing measure {mn} in fact_deliveries!"
            print(f"  - {mn}: formatString={measures[mn].get('formatString')}")

print("\n=== 4. TOTAL REPOSITORY SYNTAX VALIDATION ===")
count = 0
for root, dirs, files in os.walk('power_bi'):
    for f in files:
        if f.endswith(('.json', '.bim', '.pbip', '.pbir', '.pbism')):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8') as fp:
                json.load(fp)
            count += 1
print(f"Validated all {count} Power BI definition files: ZERO syntax errors!")
print("\nALL VERIFICATIONS PASSED CLEANLY!")
