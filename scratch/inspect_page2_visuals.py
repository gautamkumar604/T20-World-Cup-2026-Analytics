import json

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

s1 = rep['sections'][1]
print(f"=== SECTION: {s1['displayName']} ({s1['name']}) ===")
for idx, vc in enumerate(s1['visualContainers']):
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')
    print(f"\nVisual {idx+1}: {vname} ({vtype})")
    print(f"  Coordinates: x={vc.get('x')}, y={vc.get('y')}, w={vc.get('width')}, h={vc.get('height')}")
    print(f"  projections: {json.dumps(sv.get('projections', {}), indent=2)}")
    print(f"  objects: {json.dumps(sv.get('objects', {}), indent=2)}")
    if 'sortDefinition' in sv:
        print(f"  sortDefinition: {sv['sortDefinition']}")
