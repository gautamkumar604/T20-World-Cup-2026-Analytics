import json
import os

P4_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page4_TacticalAnalysis/visuals'
P3_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page3_ExecutiveOverview/visuals'
P2_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page2_Standings/visuals'
P1_DIR = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page1_Overview/visuals'

# 1. Verify Page 4 coordinates
for vf in os.listdir(P4_DIR):
    vpath = os.path.join(P4_DIR, vf, 'visual.json')
    with open(vpath, 'r', encoding='utf-8') as f:
        vdata = json.load(f)
    pos = vdata['position']
    right = pos['x'] + pos['width']
    print(f"P4 {vf:30}: x={pos['x']:4}, y={pos['y']:4}, w={pos['width']:4}, h={pos['height']:4} -> right={right:4}")
    assert right <= 1280, f"Visual {vf} exceeds 1280 width! right={right}"

# 2. Check Top 5 filters in P4 tables
for tname in ['Table_PowerplaySpecialists', 'Table_DeathSpecialists']:
    tpath = os.path.join(P4_DIR, tname, 'visual.json')
    with open(tpath, 'r', encoding='utf-8') as f:
        tdata = json.load(f)
    filters = tdata.get('filterConfig', {}).get('filters', [])
    assert len(filters) > 0, f"No filter found in {tname}!"
    f0 = filters[0]
    print(f"Verified filter in {tname}: name={f0.get('name')}, type={f0.get('type')}")
    assert 'filter' in f0, f"filter property missing in {tname}!"
    assert 'Where' in f0['filter'], f"Where missing in {tname} filter!"

# 3. Generate monolithic report.json
sections = []

pages_info = [
    (0, "ReportSection_Page1_Overview", "Tournament Overview & Standings", P1_DIR),
    (1, "ReportSection_Page2_Standings", "Official Standings", P2_DIR),
    (2, "ReportSection_Page3_ExecutiveOverview", "Executive Overview", P3_DIR),
    (3, "ReportSection_Page4_TacticalAnalysis", "Tactical Analysis", P4_DIR)
]

for sec_id, sec_name, sec_display, pdir in pages_info:
    vcs = []
    if os.path.exists(pdir):
        for vf in sorted(os.listdir(pdir)):
            vpath = os.path.join(pdir, vf, 'visual.json')
            if not os.path.exists(vpath):
                continue
            with open(vpath, 'r', encoding='utf-8') as f:
                vjson = json.load(f)
            pos = vjson.get('position', {})
            vis = vjson.get('visual', {})
            
            # Build config
            cfg = {
                "name": vjson.get('name', vf),
                "singleVisual": vis
            }
            
            # Monolithic filters
            f_list = vjson.get('filterConfig', {}).get('filters', [])
            
            vc_obj = {
                "x": pos.get('x', 0),
                "y": pos.get('y', 0),
                "z": pos.get('z', 0),
                "width": pos.get('width', 100),
                "height": pos.get('height', 100),
                "config": json.dumps(cfg),
                "filters": json.dumps(f_list)
            }
            vcs.append(vc_obj)
            
    sections.append({
        "id": sec_id,
        "name": sec_name,
        "displayName": sec_display,
        "filters": "[]",
        "ordinal": sec_id,
        "visualContainers": vcs,
        "width": 1280.0,
        "height": 720.0
    })

monolithic_report = {
    "id": 0,
    "theme": "ExecutiveSportsNavy",
    "sections": sections
}

monolithic_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(monolithic_path, 'w', encoding='utf-8') as f:
    json.dump(monolithic_report, f, indent=2, ensure_ascii=False)

print(f"\nGenerated synchronized monolithic report.json with {len(sections)} sections and {sum(len(s['visualContainers']) for s in sections)} total visual containers!")
