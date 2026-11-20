import json

with open('power_bi/T20_World_Cup_2026_Analytics.Report/report.json', 'r', encoding='utf-8') as f:
    rep = json.load(f)

for s in rep['sections']:
    print(f"=== SECTION: {s['name']} ({s.get('displayName')}) ===")
    print("Section keys:", list(s.keys()))
    for vc in s.get('visualContainers', []):
        cfg = json.loads(vc['config'])
        vname = cfg.get('name')
        vtype = cfg.get('singleVisual', {}).get('visualType')
        print(f"  Visual: {vname} | Type: {vtype} | x={vc.get('x')}, y={vc.get('y')}, w={vc.get('width')}, h={vc.get('height')}")
        if vtype in ('slicer', 'pivotTable', 'tableEx', 'clusteredColumnChart', 'clusteredBarChart'):
            print(f"    Projections: {list(cfg.get('singleVisual', {}).get('projections', {}).keys())}")
