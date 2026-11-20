import json

report_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'
with open(report_path, 'r', encoding='utf-8') as f:
    rep = json.load(f)

s2 = rep['sections'][2]
print(f"=== SECTION: {s2['displayName']} ({s2['name']}) ===")
for idx, vc in enumerate(s2['visualContainers']):
    cfg = json.loads(vc['config'])
    vname = cfg.get('name')
    sv = cfg.get('singleVisual', {})
    vtype = sv.get('visualType')
    if 'Runs' in vname or vtype == 'tableEx' or vtype == 'slicer':
        print(f"\nVisual {idx+1}: {vname} ({vtype})")
        print(f"  objects: {json.dumps(sv.get('objects', {}), indent=2)}")
        if 'sortDefinition' in sv:
            print(f"  sortDefinition: {sv['sortDefinition']}")
        if 'prototypeQuery' in sv:
            pq = sv['prototypeQuery']
            print(f"  OrderBy: {pq.get('OrderBy')}")
            print(f"  Take: {pq.get('Take')}")
